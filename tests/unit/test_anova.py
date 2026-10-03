"""Testes do teste de falta de ajuste (core/anova, issue #4)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from ensaia.core import anova
from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.model import ajustar_ols, matriz_modelo
from ensaia.core.table import Table


def _planejamento(nomes: list[str]) -> Planejamento:
    return Planejamento(
        tipo="composto_central",
        fatores=[Fator(n, -1.0, 1.0) for n in nomes],
    )


def test_erro_puro_e_graus_de_liberdade_batem_com_a_conta_manual() -> None:
    # x1 em -1, 1 e três réplicas no centro (0). Resposta no centro: 2; 2,5; 1,5
    # -> média 2,0, desvios 0; 0,5; -0,5 -> SQ erro puro = 0,5, com 2 g.l.
    y = np.array([1.0, 3.0, 2.0, 2.5, 1.5])
    dados = Table.de_colunas(
        {"x1": [-1.0, 1.0, 0.0, 0.0, 0.0], "resp": y.tolist()}
    )
    matriz = matriz_modelo(dados, _planejamento(["x1"]), ["Intercepto", "x1"])
    ajuste = ajustar_ols(matriz, y)

    falta = anova.teste_falta_ajuste(dados, "resp", ["x1"], ajuste)

    assert falta.aplicavel
    assert falta.graus_liberdade_erro_puro == 2
    assert falta.graus_liberdade_falta == ajuste.gl_residuo - 2
    assert falta.soma_quadrados_erro_puro == pytest.approx(0.5)
    assert falta.soma_quadrados_falta == pytest.approx(
        ajuste.soma_quadrados_residual - 0.5
    )

    qm_falta = falta.soma_quadrados_falta / falta.graus_liberdade_falta
    f_esperado = qm_falta / (0.5 / 2)
    assert falta.valor_f == pytest.approx(f_esperado)
    assert falta.valor_p == pytest.approx(
        float(stats.f.sf(f_esperado, falta.graus_liberdade_falta, 2))
    )
    assert falta.significativa == (falta.valor_p < 0.05)


def test_sem_replicas_nao_e_aplicavel() -> None:
    dados = Table.de_colunas(
        {"x1": [-1.0, 0.0, 1.0, 2.0], "resp": [1.0, 2.0, 3.0, 5.0]}
    )
    matriz = matriz_modelo(dados, _planejamento(["x1"]), ["Intercepto", "x1"])
    ajuste = ajustar_ols(matriz, np.array([1.0, 2.0, 3.0, 5.0]))

    falta = anova.teste_falta_ajuste(dados, "resp", ["x1"], ajuste)
    assert not falta.aplicavel
    assert falta.motivo_inaplicavel is not None
    assert "réplicas" in falta.motivo_inaplicavel


def test_modelo_sem_grau_de_liberdade_para_falta_nao_e_aplicavel() -> None:
    # 4 ensaios, 3 pontos distintos (1 réplica no centro) e 3 termos:
    # gl_residuo = 1, gl_erro_puro = 1 -> gl_falta = 0, inaplicável.
    dados = Table.de_colunas(
        {"x1": [-1.0, 1.0, 0.0, 0.0], "resp": [1.0, 3.0, 2.0, 2.4]}
    )
    matriz = matriz_modelo(dados, _planejamento(["x1"]), termos_do_modelo(["x1"]))
    ajuste = ajustar_ols(matriz, np.array([1.0, 3.0, 2.0, 2.4]))

    falta = anova.teste_falta_ajuste(dados, "resp", ["x1"], ajuste)
    assert not falta.aplicavel
    assert "grau" in (falta.motivo_inaplicavel or "")
