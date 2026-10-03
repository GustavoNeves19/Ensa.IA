"""Oráculo: o núcleo numpy tem que bater com o statsmodels (ADR 0007).

O ajuste e a ANOVA Tipo II são numpy puro para tirar o statsmodels da produção.
Para garantir que a reimplementação não desviou do comportamento consagrado,
estes testes comparam o `AjusteOLS` com o próprio statsmodels — que vive só como
dependência de teste (e traz o pandas junto, usado aqui só do lado do oráculo).

O design é deliberadamente **não-ortogonal** (pontos fora da grade de um CCD
balanceado): só aí a Tipo II difere do teste-t de cada coeficiente, então é
isto que exercita de verdade a regra de contenção de termos.
"""

from __future__ import annotations

import numpy as np
import pytest

sm = pytest.importorskip("statsmodels.api")
smf = pytest.importorskip("statsmodels.formula.api")
pd = pytest.importorskip("pandas")
from statsmodels.stats.anova import anova_lm  # noqa: E402

from ensaia.core.model import RESIDUO, ajustar_ols  # noqa: E402
from ensaia.core.table import Table  # noqa: E402

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


def _dados_nao_ortogonais() -> tuple[Table, np.ndarray, np.ndarray, np.ndarray]:
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
    matriz = Table.de_colunas(
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
    y = 10.0 + 2.0 * x1 - 1.5 * x2 + 0.8 * x1**2 + ruido
    return matriz, y, x1, x2


def _como_array(matriz: Table) -> np.ndarray:
    return np.column_stack([matriz.coluna(t) for t in matriz.colunas])


def test_fit_bate_com_statsmodels() -> None:
    matriz, y, _, _ = _dados_nao_ortogonais()
    ajuste = ajustar_ols(matriz, y)

    oraculo = sm.OLS(y, _como_array(matriz)).fit()
    termos = ajuste.termos

    assert np.array([ajuste.coeficientes[t] for t in termos]) == pytest.approx(
        oraculo.params, rel=1e-8
    )
    assert np.array([ajuste.erros_padrao[t] for t in termos]) == pytest.approx(
        oraculo.bse, rel=1e-8
    )
    assert np.array([ajuste.valores_t[t] for t in termos]) == pytest.approx(
        oraculo.tvalues, rel=1e-8
    )
    assert np.array([ajuste.valores_p[t] for t in termos]) == pytest.approx(
        oraculo.pvalues, rel=1e-7, abs=1e-14
    )
    assert ajuste.r2 == pytest.approx(oraculo.rsquared, rel=1e-9)
    assert ajuste.r2_ajustado == pytest.approx(oraculo.rsquared_adj, rel=1e-9)


def test_tipo_ii_bate_com_anova_lm() -> None:
    matriz, y, x1, x2 = _dados_nao_ortogonais()
    tabela = {linha.fonte: linha for linha in ajustar_ols(matriz, y).tabela_tipo2()}

    dados = pd.DataFrame({"x1": x1, "x2": x2, "y": y})
    formula = "y ~ " + " + ".join(_PARA_PATSY[t] for t in TERMOS if t != "Intercepto")
    oraculo = anova_lm(smf.ols(formula, data=dados).fit(), typ=2)

    assert tabela[RESIDUO].graus_liberdade == int(oraculo.loc["Residual", "df"])
    assert tabela[RESIDUO].soma_quadrados == pytest.approx(
        oraculo.loc["Residual", "sum_sq"], rel=1e-8
    )

    for nome_patsy in oraculo.index:
        if nome_patsy == "Residual":
            continue
        linha = tabela[_canonico(str(nome_patsy))]
        assert linha.soma_quadrados == pytest.approx(
            oraculo.loc[nome_patsy, "sum_sq"], rel=1e-8
        )
        assert linha.valor_f == pytest.approx(oraculo.loc[nome_patsy, "F"], rel=1e-8)
        assert linha.valor_p == pytest.approx(
            oraculo.loc[nome_patsy, "PR(>F)"], rel=1e-7, abs=1e-14
        )
