"""Oráculo: o núcleo numpy tem que bater com o statsmodels (ADR 0007).

O ajuste e a ANOVA Tipo II foram reescritos em numpy puro para tirar o
statsmodels da produção. Para garantir que a reimplementação não desviou do
comportamento consagrado, estes testes comparam o `AjusteOLS` com o próprio
statsmodels — que agora vive só como dependência de teste.

O design é deliberadamente **não-ortogonal** (pontos fora da grade de um CCD
balanceado): só aí a Tipo II difere do teste-t de cada coeficiente, então é
isto que exercita de verdade a regra de contenção de termos. Num design
simétrico a comparação passaria sem testar nada.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

sm = pytest.importorskip("statsmodels.api")
smf = pytest.importorskip("statsmodels.formula.api")
from statsmodels.stats.anova import anova_lm  # noqa: E402

from ensaia.core.model import RESIDUO, ajustar_ols  # noqa: E402

# Nomes canônicos do EnsaIA -> sintaxe patsy, para o ajuste-oráculo por fórmula.
_PARA_PATSY = {
    "x1": "x1",
    "x2": "x2",
    "x1^2": "I(x1 ** 2)",
    "x2^2": "I(x2 ** 2)",
    "x1:x2": "x1:x2",
}
# Normalizado sem espaços: o patsy às vezes devolve "I(x1 ** 2)" com espaços
# variáveis, então a chave de busca ignora espaço.
_DE_PATSY = {v.replace(" ", ""): k for k, v in _PARA_PATSY.items()}
TERMOS = ["Intercepto", "x1", "x2", "x1^2", "x2^2", "x1:x2"]


def _canonico(nome_patsy: str) -> str:
    return _DE_PATSY[nome_patsy.replace(" ", "")]


def _dados_nao_ortogonais() -> tuple[pd.DataFrame, pd.Series]:
    """11 ensaios irregulares: colunas correlacionadas, posto cheio, 5 gl de resíduo."""
    pontos = [
        (-1.0, -1.0),
        (1.0, -1.0),
        (-1.0, 1.0),
        (1.0, 1.0),
        (-1.0, 0.0),
        (1.0, 0.0),
        (0.0, -1.0),
        (0.0, 1.0),
        (0.0, 0.0),
        (0.5, 0.5),
        (-0.5, 0.3),
    ]
    x1 = np.array([p[0] for p in pontos])
    x2 = np.array([p[1] for p in pontos])
    matriz = pd.DataFrame(
        {
            "Intercepto": np.ones(len(pontos)),
            "x1": x1,
            "x2": x2,
            "x1^2": x1**2,
            "x2^2": x2**2,
            "x1:x2": x1 * x2,
        }
    )
    ruido = np.random.default_rng(3).normal(0.0, 0.5, len(pontos))
    y = pd.Series(10.0 + 2.0 * x1 - 1.5 * x2 + 0.8 * x1**2 + ruido)
    return matriz, y


def test_fit_bate_com_statsmodels() -> None:
    matriz, y = _dados_nao_ortogonais()
    ajuste = ajustar_ols(matriz, y)

    oraculo = sm.OLS(y.to_numpy(), matriz.to_numpy()).fit()

    assert ajuste.coeficientes.to_numpy() == pytest.approx(oraculo.params, rel=1e-8)
    assert ajuste.erros_padrao.to_numpy() == pytest.approx(oraculo.bse, rel=1e-8)
    assert ajuste.valores_t.to_numpy() == pytest.approx(oraculo.tvalues, rel=1e-8)
    assert ajuste.valores_p.to_numpy() == pytest.approx(
        oraculo.pvalues, rel=1e-7, abs=1e-14
    )
    assert ajuste.r2 == pytest.approx(oraculo.rsquared, rel=1e-9)
    assert ajuste.r2_ajustado == pytest.approx(oraculo.rsquared_adj, rel=1e-9)


def test_tipo_ii_bate_com_anova_lm() -> None:
    matriz, y = _dados_nao_ortogonais()
    tabela = ajustar_ols(matriz, y).tabela_tipo2()

    dados = pd.DataFrame({"x1": matriz["x1"], "x2": matriz["x2"], "y": y.to_numpy()})
    formula = "y ~ " + " + ".join(_PARA_PATSY[t] for t in TERMOS if t != "Intercepto")
    oraculo = anova_lm(smf.ols(formula, data=dados).fit(), typ=2)

    # A linha de resíduo tem que casar.
    assert tabela.loc[RESIDUO, "graus_liberdade"] == int(oraculo.loc["Residual", "df"])
    assert tabela.loc[RESIDUO, "soma_quadrados"] == pytest.approx(
        oraculo.loc["Residual", "sum_sq"], rel=1e-8
    )

    # Cada termo: soma de quadrados, F e p idênticos ao statsmodels.
    for nome_patsy in oraculo.index:
        if nome_patsy == "Residual":
            continue
        canonico = _canonico(str(nome_patsy))
        assert tabela.loc[canonico, "soma_quadrados"] == pytest.approx(
            oraculo.loc[nome_patsy, "sum_sq"], rel=1e-8
        )
        assert tabela.loc[canonico, "valor_f"] == pytest.approx(
            oraculo.loc[nome_patsy, "F"], rel=1e-8
        )
        assert tabela.loc[canonico, "valor_p"] == pytest.approx(
            oraculo.loc[nome_patsy, "PR(>F)"], rel=1e-7, abs=1e-14
        )
