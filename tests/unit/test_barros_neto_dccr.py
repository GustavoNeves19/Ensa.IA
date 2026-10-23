"""Datasets dourados de Barros Neto, Scarminio e Bruns (2010), capítulo 6.

Valida o pipeline inteiro (OLS, ANOVA, R², R² máximo, falta de ajuste, regra
dos 10x de Box-Wetz) contra exemplos publicados no livro-texto de DCCR citado
no TCC. Ver `docs/pesquisa/barros-neto-dccr.md` seção 16 para a proveniência
de cada número: [LIVRO] é publicado pelos autores, [CALCULADO] é a
recomputação de referência (numpy/scipy) feita ao revisar o livro.

Os fatores usam Fator(nome, -1.0, 1.0): os dados já entram na escala
codificada do livro, então `codificar()` é a identidade e os pontos axiais
(±1,4, ±1,682 etc.) passam direto, sem distorção de escala.
"""

from __future__ import annotations

import pytest

from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.pipeline import analisar
from ensaia.core.table import Table


def _planejamento(nomes: list[str]) -> Planejamento:
    return Planejamento(
        tipo="composto_central",
        fatores=[Fator(n, -1.0, 1.0) for n in nomes],
    )


def test_tabela_6_7_rendimento_concentracao_agitacao() -> None:
    """k=2, DCCR com alfa=√2, 3 pontos centrais, n=11 (livro, p. 276-278)."""
    x1 = [-1, 1, -1, 1, 0, 0, 0, -1.4142, 0, 1.4142, 0]
    x2 = [-1, -1, 1, 1, 0, 0, 0, 0, 1.4142, 0, -1.4142]
    y = [86, 85, 78, 84, 90, 88, 89, 81, 80, 86, 87]
    tabela = Table.de_colunas({"x1": x1, "x2": x2, "y": y})
    termos = termos_do_modelo(["x1", "x2"])

    resultado = analisar(
        tabela, _planejamento(["x1", "x2"]), termos, ["y"], versao_ensaia="test"
    )
    ajuste = resultado.ajustes[0]
    coef = {c.termo: c.estimativa for c in ajuste.coeficientes}

    # [CALCULADO] (docs/pesquisa/barros-neto-dccr.md §16.1).
    assert coef["Intercepto"] == pytest.approx(89.0000, abs=1e-3)
    assert coef["x1"] == pytest.approx(1.5089, abs=1e-3)
    assert coef["x2"] == pytest.approx(-2.3624, abs=1e-3)
    assert coef["x1^2"] == pytest.approx(-2.8125, abs=1e-3)
    assert coef["x2^2"] == pytest.approx(-2.8125, abs=1e-3)
    assert coef["x1:x2"] == pytest.approx(1.7500, abs=1e-3)

    # [LIVRO] Tabela 6.8, p. 278: % explicada 98,12; % máxima explicável 98,64.
    assert ajuste.r2 == pytest.approx(0.9812, abs=2e-4)
    assert ajuste.r2_maximo == pytest.approx(0.9864, abs=2e-4)
    assert ajuste.r2_ajustado == pytest.approx(0.9624, abs=1e-3)
    assert ajuste.r2_predicao == pytest.approx(0.9325, abs=1e-3)

    reg = ajuste.anova_regressao
    assert reg is not None
    # [CALCULADO]: F_reg = 52,18 contra F(5,5) = 5,05 -> razão 10,3.
    regressao = next(li for li in reg.linhas if li.fonte == "Regressão")
    assert regressao.valor_f == pytest.approx(52.18, rel=1e-2)
    assert reg.f_tabelado == pytest.approx(5.05, rel=1e-2)
    assert reg.razao_f == pytest.approx(10.3, rel=2e-2)
    assert reg.regressao_significativa is True
    # Razão > 10: regra de Box-Wetz (p. 238) classifica como útil p/ previsão.
    assert reg.util_para_previsao is True

    # [CALCULADO]: F_faj = 0,254 contra F(3,2) = 19,16 (p = 0,855): sem falta de ajuste.
    falta = ajuste.falta_de_ajuste
    assert falta.aplicavel
    assert falta.valor_f == pytest.approx(0.254, rel=5e-2)
    assert falta.significativa is False


def test_6a1_sinal_catalitico_mo_vi_com_erro_puro() -> None:
    """k=2, alfa=1,4, 5 centros, n=13 (livro, p. 299-300).

    Caso em que o quadrático melhora muito o ajuste mas AINDA tem falta de
    ajuste significativa — o sinal do sistema precisa acusar isso, não só
    reportar "sem falta de ajuste" por omissão.
    """
    x1 = [-1, 1, -1, 1, -1.4, 1.4, 0, 0, 0, 0, 0, 0, 0]
    x2 = [-1, -1, 1, 1, 0, 0, -1.4, 1.4, 0, 0, 0, 0, 0]
    y = [
        0.373, 0.497, 0.483, 0.615, 0.308, 0.555, 0.465, 0.628,
        0.538, 0.549, 0.536, 0.549, 0.538,
    ]
    tabela = Table.de_colunas({"x1": x1, "x2": x2, "y": y})
    termos = termos_do_modelo(["x1", "x2"])

    resultado = analisar(
        tabela,
        _planejamento(["x1", "x2"]),
        termos,
        ["y"],
        versao_ensaia="test",
        termo_erro="erro_puro",
    )
    ajuste = resultado.ajustes[0]
    coef = {c.termo: c.estimativa for c in ajuste.coeficientes}

    # [LIVRO], p. 300.
    assert coef["Intercepto"] == pytest.approx(0.542, abs=2e-3)
    assert coef["x1"] == pytest.approx(0.076, abs=2e-3)
    assert coef["x2"] == pytest.approx(0.058, abs=2e-3)
    assert coef["x1^2"] == pytest.approx(-0.055, abs=2e-3)
    assert coef["x2^2"] == pytest.approx(0.003, abs=2e-3)
    assert coef["x1:x2"] == pytest.approx(0.002, abs=2e-3)

    # Erros-padrão com erro puro [CALCULADO] coincidem com os do livro
    # (seção 9 de barros-neto-dccr.md: os exemplos do livro usam MQ_ep, não MQ_r).
    erros = {c.termo: c.erro_padrao for c in ajuste.coeficientes}
    assert erros["Intercepto"] == pytest.approx(0.0029, rel=0.1)
    assert erros["x1"] == pytest.approx(0.0023, rel=0.1)
    assert erros["x1^2"] == pytest.approx(0.0025, rel=0.1)
    assert ajuste.termo_erro == "erro_puro"

    # [LIVRO]: significativos x1, x1², x2; não significativos x2², x1x2.
    sig = {c.termo: c.significativo for c in ajuste.coeficientes}
    assert sig["x1"] is True
    assert sig["x1^2"] is True
    assert sig["x2"] is True
    assert sig["x2^2"] is False
    assert sig["x1:x2"] is False

    # [CALCULADO]: R²=98,56%; R² máximo=99,82%.
    assert ajuste.r2 == pytest.approx(0.9856, abs=5e-4)
    assert ajuste.r2_maximo == pytest.approx(0.9982, abs=5e-4)

    # [LIVRO] p. 300: MQ_faj/MQ_ep = 9,6 > F(3,4) = 6,59 -> AINDA há falta de
    # ajuste, apesar do quadrático ser muito melhor que o linear.
    falta = ajuste.falta_de_ajuste
    assert falta.aplicavel
    assert falta.valor_f == pytest.approx(9.6, rel=0.1)
    assert falta.significativa is True


def test_6a2_desidratacao_osmotica_abacaxi() -> None:
    """k=3, alfa=1,682, 5 centros, n=19 (livro, p. 301-303).

    Caso com razão F_calc/F_tab = 6,5: regressão significativa, mas abaixo do
    limiar de ~10x de Box-Wetz — não "útil para previsão" no critério mais
    exigente, distinto da significância.
    """
    x1 = [-1, 1, -1, 1, -1, 1, -1, 1, -1.682, 1.682, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    x2 = [-1, -1, 1, 1, -1, -1, 1, 1, 0, 0, -1.682, 1.682, 0, 0, 0, 0, 0, 0, 0]
    x3 = [-1, -1, -1, -1, 1, 1, 1, 1, 0, 0, 0, 0, -1.682, 1.682, 0, 0, 0, 0, 0]
    y = [
        47.34, 53.00, 53.64, 54.28, 48.85, 53.73, 55.19, 58.31,
        51.90, 57.34, 47.62, 57.35, 50.73, 57.68,
        56.24, 55.74, 57.23, 56.85, 55.42,
    ]
    tabela = Table.de_colunas({"x1": x1, "x2": x2, "x3": x3, "y": y})
    termos = termos_do_modelo(["x1", "x2", "x3"])

    resultado = analisar(
        tabela, _planejamento(["x1", "x2", "x3"]), termos, ["y"], versao_ensaia="test"
    )
    ajuste = resultado.ajustes[0]
    coef = {c.termo: c.estimativa for c in ajuste.coeficientes}

    # [LIVRO], p. 303.
    assert coef["Intercepto"] == pytest.approx(56.32, abs=0.02)
    assert coef["x1"] == pytest.approx(1.72, abs=0.02)
    assert coef["x2"] == pytest.approx(2.55, abs=0.02)
    assert coef["x3"] == pytest.approx(1.43, abs=0.02)
    assert coef["x1^2"] == pytest.approx(-0.71, abs=0.02)
    assert coef["x2^2"] == pytest.approx(-1.47, abs=0.02)
    assert coef["x3^2"] == pytest.approx(-0.86, abs=0.02)
    assert coef["x1:x2"] == pytest.approx(-0.85, abs=0.02)
    assert coef["x1:x3"] == pytest.approx(0.21, abs=0.02)
    assert coef["x2:x3"] == pytest.approx(0.42, abs=0.02)

    # [CALCULADO]: R²=95,39%; R² máximo=98,94%; R² ajustado=0,9078.
    assert ajuste.r2 == pytest.approx(0.9539, abs=5e-4)
    assert ajuste.r2_maximo == pytest.approx(0.9894, abs=5e-4)
    assert ajuste.r2_ajustado == pytest.approx(0.9078, abs=2e-3)

    reg = ajuste.anova_regressao
    assert reg is not None
    assert reg.regressao_significativa is True
    # [LIVRO] p. 303: "mais de 6 vezes" F(9,9) -> abaixo do limiar de ~10x.
    assert reg.razao_f == pytest.approx(6.5, rel=0.1)
    assert reg.util_para_previsao is False

    # [LIVRO] p. 303: sem falta de ajuste a 95% (MQ_faj/MQ_ep = 2,66).
    falta = ajuste.falta_de_ajuste
    assert falta.aplicavel
    assert falta.valor_f == pytest.approx(2.66, rel=0.1)
    assert falta.significativa is False
