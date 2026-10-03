"""Testes de coeficientes, efeitos e intervalos de confiança (issue #5)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from lyra.core.design import Fator, Planejamento, termos_do_modelo
from lyra.core.effects import efeitos_principais, extrair_coeficientes
from lyra.core.model import ajustar_ols, matriz_modelo

BETA_VERDADEIRO = {
    "Intercepto": 50.0,
    "x1": 3.0,
    "x2": -2.0,
    "x3": 5.0,
    "x1^2": -4.0,
    "x2^2": 1.5,
    "x3^2": -2.0,
    "x1:x2": 2.5,
    "x1:x3": -1.0,
    "x2:x3": 0.8,
}


def _planejamento(nomes: list[str]) -> Planejamento:
    return Planejamento(
        tipo="composto_central",
        fatores=[Fator(nome=n, minimo=-1.0, maximo=1.0) for n in nomes],
        n_pontos_centrais=3,
        alfa_axial=1.68,
    )


def _ccd_3_fatores() -> pd.DataFrame:
    a = 1.68
    fatorial = [(i, j, k) for i in (-1, 1) for j in (-1, 1) for k in (-1, 1)]
    axiais = [(-a, 0, 0), (a, 0, 0), (0, -a, 0), (0, a, 0), (0, 0, -a), (0, 0, a)]
    centrais = [(0, 0, 0)] * 3
    return pd.DataFrame(
        fatorial + axiais + centrais, columns=["x1", "x2", "x3"], dtype=float
    )


@pytest.fixture
def ajuste_ccd():
    dados = _ccd_3_fatores()
    termos = list(BETA_VERDADEIRO)
    matriz = matriz_modelo(dados, _planejamento(["x1", "x2", "x3"]), termos)
    ruido = np.random.default_rng(7).normal(0.0, 0.8, len(dados))
    y = pd.Series(
        matriz.to_numpy() @ np.array(list(BETA_VERDADEIRO.values())) + ruido,
        index=matriz.index,
    )
    return ajustar_ols(matriz, y)


def test_coeficientes_saem_na_ordem_e_notacao_canonica(ajuste_ccd) -> None:
    coefs = extrair_coeficientes(ajuste_ccd)
    assert [c.termo for c in coefs] == list(BETA_VERDADEIRO)


def test_coeficientes_recuperam_o_beta_verdadeiro(ajuste_ccd) -> None:
    """Com ruído pequeno, as estimativas ficam perto do β que gerou os dados."""
    coefs = {c.termo: c.estimativa for c in extrair_coeficientes(ajuste_ccd)}
    for termo, verdadeiro in BETA_VERDADEIRO.items():
        assert coefs[termo] == pytest.approx(verdadeiro, abs=0.6)


def test_coeficientes_batem_com_o_ajuste_canonico(ajuste_ccd) -> None:
    """Estimativa, erro, t e p vêm do ajuste canônico, não do sombra."""
    coefs = extrair_coeficientes(ajuste_ccd)
    esperado_coef = ajuste_ccd.coeficientes
    esperado_erro = ajuste_ccd.erros_padrao
    esperado_t = ajuste_ccd.valores_t
    esperado_p = ajuste_ccd.valores_p
    for c in coefs:
        assert c.estimativa == pytest.approx(float(esperado_coef[c.termo]))
        assert c.erro_padrao == pytest.approx(float(esperado_erro[c.termo]))
        assert c.valor_t == pytest.approx(float(esperado_t[c.termo]))
        assert c.valor_p == pytest.approx(float(esperado_p[c.termo]))


def test_intervalo_confianca_contem_a_estimativa(ajuste_ccd) -> None:
    for c in extrair_coeficientes(ajuste_ccd, alfa=0.05):
        assert c.ic_inferior is not None and c.ic_superior is not None
        assert c.ic_inferior < c.estimativa < c.ic_superior


def test_sem_ic_quando_nao_pedido(ajuste_ccd) -> None:
    for c in extrair_coeficientes(ajuste_ccd, calcular_ic=False):
        assert c.ic_inferior is None
        assert c.ic_superior is None


def test_significancia_usa_o_alfa_informado(ajuste_ccd) -> None:
    for c in extrair_coeficientes(ajuste_ccd, alfa=0.01):
        assert c.significativo == (c.valor_p < 0.01)


def test_efeito_e_o_dobro_do_coeficiente_so_nos_principais(ajuste_ccd) -> None:
    coefs = extrair_coeficientes(ajuste_ccd)
    por_termo = {c.termo: c.estimativa for c in coefs}
    efeitos = efeitos_principais(coefs)

    # Só efeitos principais lineares entram, e valem 2 × coeficiente.
    assert set(efeitos) == {"x1", "x2", "x3"}
    for fator in ("x1", "x2", "x3"):
        assert efeitos[fator] == pytest.approx(2.0 * por_termo[fator])


def test_efeitos_ignoram_intercepto_quadraticos_e_interacoes() -> None:
    nomes = ["a", "b"]
    termos = termos_do_modelo(nomes)  # Intercepto, a, b, a^2, b^2, a:b
    dados = pd.DataFrame(
        [(i, j) for i in (-1.0, 0.0, 1.0) for j in (-1.0, 0.0, 1.0)],
        columns=nomes,
    )
    matriz = matriz_modelo(dados, _planejamento(nomes), termos)
    y = pd.Series(
        matriz.to_numpy() @ np.array([10.0, 2.0, -3.0, 1.0, -1.0, 4.0]),
        index=matriz.index,
    )
    efeitos = efeitos_principais(extrair_coeficientes(ajustar_ols(matriz, y)))
    assert set(efeitos) == {"a", "b"}
