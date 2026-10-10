"""Testes do diagnóstico de resíduos (core/diagnostico)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from ensaia.core.diagnostico import diagnosticar, pontos_qq


def test_residuo_e_observado_menos_predito_na_ordem_da_planilha() -> None:
    d = diagnosticar(np.array([10.0, 12.0, 9.0]), np.array([9.5, 12.5, 9.0]))
    assert d.observados == [10.0, 12.0, 9.0]
    assert d.preditos == [9.5, 12.5, 9.0]
    assert d.residuos == pytest.approx([0.5, -0.5, 0.0])


def test_shapiro_bate_com_o_scipy() -> None:
    rng = np.random.default_rng(7)
    y = rng.normal(50.0, 2.0, size=12)
    y_chapeu = np.full(12, 50.0)
    d = diagnosticar(y, y_chapeu)
    esperado = stats.shapiro(y - y_chapeu)
    assert d.shapiro_w == pytest.approx(float(esperado.statistic))
    assert d.shapiro_p == pytest.approx(float(esperado.pvalue))
    assert d.motivo_sem_shapiro is None
    assert d.normalidade_rejeitada == (float(esperado.pvalue) < 0.05)


def test_normalidade_rejeitada_segue_o_alfa() -> None:
    # Resíduos claramente assimétricos: Shapiro rejeita.
    y = np.array([0.0] * 9 + [10.0, 12.0, 30.0])
    d = diagnosticar(y, np.zeros(12), alfa=0.05)
    assert d.shapiro_p is not None and d.shapiro_p < 0.05
    assert d.normalidade_rejeitada is True
    # Com α minúsculo, a mesma evidência não basta para rejeitar.
    d2 = diagnosticar(y, np.zeros(12), alfa=1e-12)
    assert d2.normalidade_rejeitada is False


def test_shapiro_inaplicavel_com_poucos_ensaios() -> None:
    d = diagnosticar(np.array([1.0, 2.0]), np.array([1.1, 1.9]))
    assert d.shapiro_w is None and d.shapiro_p is None
    assert d.normalidade_rejeitada is None
    assert "3 ensaios" in (d.motivo_sem_shapiro or "")


def test_shapiro_inaplicavel_em_ajuste_exato() -> None:
    y = np.array([1.0, 2.0, 3.0, 4.0])
    d = diagnosticar(y, y.copy())
    assert d.shapiro_w is None
    assert "todos iguais" in (d.motivo_sem_shapiro or "")


def test_tamanhos_diferentes_falham_claro() -> None:
    with pytest.raises(ValueError, match="tamanhos diferentes"):
        diagnosticar(np.array([1.0, 2.0, 3.0]), np.array([1.0, 2.0]))


def test_qq_ordena_residuos_e_guarda_o_ensaio_de_origem() -> None:
    qq = pontos_qq([0.3, -1.2, 0.8, -0.1])
    assert qq.amostrais == [-1.2, -0.1, 0.3, 0.8]
    assert qq.ensaios == [2, 4, 1, 3]  # linhas da planilha, contando de 1
    # Quantis teóricos crescentes e simétricos em torno de zero (Blom).
    assert qq.teoricos == sorted(qq.teoricos)
    assert qq.teoricos[0] == pytest.approx(-qq.teoricos[-1])
    n = 4
    assert qq.teoricos[0] == pytest.approx(stats.norm.ppf((1 - 0.375) / (n + 0.25)))


def test_qq_reta_passa_pelos_quartis() -> None:
    residuos = [-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
    qq = pontos_qq(residuos)
    x1, x2 = stats.norm.ppf([0.25, 0.75])
    y1, y2 = np.quantile(residuos, [0.25, 0.75])
    assert qq.reta_intercepto + qq.reta_inclinacao * x1 == pytest.approx(y1)
    assert qq.reta_intercepto + qq.reta_inclinacao * x2 == pytest.approx(y2)


def test_qq_residuos_iguais_nao_divide_por_zero() -> None:
    qq = pontos_qq([0.0, 0.0, 0.0])
    assert qq.reta_inclinacao == 0.0
    assert qq.reta_intercepto == 0.0
