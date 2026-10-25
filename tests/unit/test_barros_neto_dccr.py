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


# 6A.3, na ordem das colunas do CSV de barros-neto-dccr.md §16.4. Atenção: o
# texto do resumo diz que os termos significativos são os de x1 e x3, mas, com
# o CSV como está, são os de x1 e x4: os coeficientes [CALCULADO] que o resumo
# chama de "x3" saem na 4ª coluna. A 3ª e a 4ª colunas do CSV estão trocadas
# em relação aos rótulos do resumo; conferir no livro (p. 304) antes de citar.
_COLESTEROL_X = [
    (-1, -1, -1, -1), (1, -1, -1, -1), (-1, 1, -1, -1), (1, 1, -1, -1),
    (-1, -1, 1, -1), (1, -1, 1, -1), (-1, 1, 1, -1), (1, 1, 1, -1),
    (-1, -1, -1, 1), (1, -1, -1, 1), (-1, 1, -1, 1), (1, 1, -1, 1),
    (-1, -1, 1, 1), (1, -1, 1, 1), (-1, 1, 1, 1), (1, 1, 1, 1),
    (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0),
    (-2, 0, 0, 0), (2, 0, 0, 0), (0, -2, 0, 0), (0, 2, 0, 0),
    (0, 0, -2, 0), (0, 0, 2, 0), (0, 0, 0, -2), (0, 0, 0, 2),
    (0, 0, 0, 0), (0, 0, 0, 0),
]  # fmt: skip
_COLESTEROL_Y = [
    1.701, 1.120, 1.607, 0.881, 1.860, 0.965, 1.786, 0.933,
    2.131, 2.072, 2.095, 2.002, 2.101, 2.055, 2.017, 1.972,
    1.763, 1.840, 1.935, 1.713, 1.089, 1.643, 1.601, 1.691, 1.648,
    0.675, 2.049, 1.783, 1.983,
]  # fmt: skip
_NOMES_COLESTEROL = ["x1", "x2", "x3", "x4"]


def _colunas_colesterol() -> dict[str, list[float]]:
    return {
        n: [float(p[j]) for p in _COLESTEROL_X]
        for j, n in enumerate(_NOMES_COLESTEROL)
    }


def _colesterol() -> Table:
    return Table.de_colunas({**_colunas_colesterol(), "y": _COLESTEROL_Y})


def test_6a3_colesterol_quatro_fatores() -> None:
    """k=4, alfa=2, 5 centros, n=29 (livro, p. 303-306)."""
    resultado = analisar(
        _colesterol(),
        _planejamento(_NOMES_COLESTEROL),
        termos_do_modelo(_NOMES_COLESTEROL),
        ["y"],
        versao_ensaia="test",
    )
    ajuste = resultado.ajustes[0]
    coef = {c.termo: c.estimativa for c in ajuste.coeficientes}

    # [CALCULADO] quadrático completo (§16.4), que o livro publica como
    # "modelo reduzido" sem reajustar.
    assert coef["Intercepto"] == pytest.approx(1.8608, abs=1e-4)
    assert coef["x1"] == pytest.approx(-0.1894, abs=1e-4)
    assert coef["x4"] == pytest.approx(0.3475, abs=1e-4)
    assert coef["x1^2"] == pytest.approx(-0.0829, abs=1e-4)
    assert coef["x4^2"] == pytest.approx(-0.0926, abs=1e-4)
    assert coef["x1:x4"] == pytest.approx(0.1757, abs=1e-4)

    # [LIVRO] p. 303-304: explica 94,3%, sem falta de ajuste a 95%.
    assert ajuste.r2 == pytest.approx(0.943, abs=5e-4)
    assert ajuste.r2_maximo == pytest.approx(0.9926, abs=5e-4)
    falta = ajuste.falta_de_ajuste
    assert (falta.graus_liberdade_falta, falta.graus_liberdade_erro_puro) == (10, 4)
    assert falta.valor_f == pytest.approx(2.68, rel=1e-2)
    assert falta.significativa is False

    # [LIVRO]: só os termos dos dois fatores fortes são significativos.
    significativos = {c.termo for c in ajuste.coeficientes if c.significativo}
    assert significativos == {"Intercepto", "x1", "x4", "x1^2", "x4^2", "x1:x4"}


def test_6a3_modelo_reduzido_e_reajustado() -> None:
    """ADR 0014: o EnsaIA reajusta ao reduzir; o livro não reajusta (p. 304)."""
    reduzido = ["Intercepto", "x1", "x4", "x1^2", "x4^2", "x1:x4"]
    resultado = analisar(
        _colesterol(),
        _planejamento(_NOMES_COLESTEROL),
        reduzido,
        ["y"],
        versao_ensaia="test",
    )
    coef = {c.termo: c.estimativa for c in resultado.ajustes[0].coeficientes}
    # [CALCULADO] §16.4: ao reajustar, b0 e os quadráticos mudam; os lineares e
    # a interação não (colunas ortogonais às removidas).
    assert coef["Intercepto"] == pytest.approx(1.8135, abs=1e-4)
    assert coef["x1^2"] == pytest.approx(-0.0760, abs=1e-4)
    assert coef["x4^2"] == pytest.approx(-0.0857, abs=1e-4)
    assert coef["x1"] == pytest.approx(-0.1894, abs=1e-4)
    assert coef["x1:x4"] == pytest.approx(0.1757, abs=1e-4)


_LACASE_X1 = [
    -1, -1, 1, 1, -1, -1, 1, 1, 0, 0,
    0, 0, -1.41, -1.41, 0, 0, 1.41, 1.41, 0, 0,
]  # fmt: skip
_LACASE_X2 = [
    -1, -1, -1, -1, 1, 1, 1, 1, 0, 0,
    0, 0, 0, 0, 1.41, 1.41, 0, 0, -1.41, -1.41,
]  # fmt: skip


def test_6a4_lacase_com_duplicatas_e_erro_puro() -> None:
    """k=2, alfa=1,41, n=20, todos os pontos em duplicata e 4 centros (p. 307-308).

    Com todos os pontos repetidos, o erro puro tem 11 graus de liberdade.
    """
    y = [
        3.50, 3.20, 1.17, 1.70, 4.10, 5.40, 1.90, 2.10, 4.80, 5.00,
        4.70, 5.20, 5.25, 5.41, 6.00, 3.20, 2.30, 1.60, 0.50, 0.50,
    ]  # fmt: skip
    tabela = Table.de_colunas({"x1": _LACASE_X1, "x2": _LACASE_X2, "y": y})
    resultado = analisar(
        tabela,
        _planejamento(["x1", "x2"]),
        termos_do_modelo(["x1", "x2"]),
        ["y"],
        versao_ensaia="test",
        termo_erro="erro_puro",
    )
    ajuste = resultado.ajustes[0]
    coef = {c.termo: c for c in ajuste.coeficientes}

    # [LIVRO] p. 307: coeficientes e erros-padrão (calculados com o erro puro).
    publicados = {
        "Intercepto": (4.93, 0.35),
        "x1": (-1.18, 0.18),
        "x2": (0.97, 0.18),
        "x1^2": (-0.70, 0.23),
        "x2^2": (-1.25, 0.23),
        "x1:x2": (-0.21, 0.25),
    }
    for termo, (b, ep) in publicados.items():
        assert coef[termo].estimativa == pytest.approx(b, abs=0.006)
        assert coef[termo].erro_padrao == pytest.approx(ep, abs=0.006)

    # [LIVRO]: todos significativos, exceto a interação.
    assert {t for t, c in coef.items() if not c.significativo} == {"x1:x2"}

    # [LIVRO]: explica 84,9%; máximo explicável 91,2%; sem falta de ajuste.
    assert ajuste.r2 == pytest.approx(0.849, abs=5e-4)
    assert ajuste.r2_maximo == pytest.approx(0.912, abs=5e-4)
    # [CALCULADO]: R² ajustado 0,7956; R² de predição 0,6824.
    assert ajuste.r2_ajustado == pytest.approx(0.7956, abs=5e-4)
    assert ajuste.r2_predicao == pytest.approx(0.6824, abs=5e-4)
    falta = ajuste.falta_de_ajuste
    # O resumo escreve F(5, 11), mas a falta de ajuste tem 3 g.l. (9 condições
    # distintas − 6 parâmetros); 3,59 é o F(3, 11) a 95%.
    assert (falta.graus_liberdade_falta, falta.graus_liberdade_erro_puro) == (3, 11)
    assert falta.valor_f == pytest.approx(2.63, abs=0.01)
    assert falta.valor_p == pytest.approx(0.10, abs=0.01)
    assert falta.significativa is False


def test_tabela_6_7_ponto_otimo_e_um_maximo() -> None:
    """Exercício 6.8 e Figura 6.6 (p. 277-278): máximo em (0,15; −0,37), ŷ ≈ 89,6."""
    x1 = [-1, 1, -1, 1, 0, 0, 0, -1.4142, 0, 1.4142, 0]
    x2 = [-1, -1, 1, 1, 0, 0, 0, 0, 1.4142, 0, -1.4142]
    y = [86, 85, 78, 84, 90, 88, 89, 81, 80, 86, 87]
    tabela = Table.de_colunas({"x1": x1, "x2": x2, "y": y})
    resultado = analisar(
        tabela,
        _planejamento(["x1", "x2"]),
        termos_do_modelo(["x1", "x2"]),
        ["y"],
        versao_ensaia="test",
    )
    pe = resultado.ajustes[0].ponto_estacionario
    assert pe is not None
    assert pe.codificado["x1"] == pytest.approx(0.15, abs=0.005)
    assert pe.codificado["x2"] == pytest.approx(-0.37, abs=0.005)
    assert pe.resposta_prevista == pytest.approx(89.6, abs=0.05)
    assert pe.natureza == "maximo"
    assert pe.dentro_da_regiao is True
    # [CALCULADO]: autovalores negativos (−1,94; −3,69).
    assert sorted(pe.autovalores) == pytest.approx([-3.69, -1.94], abs=0.01)


_EXEMPLOS_DO_LIVRO = {
    "tabela-6.7-k2": {
        "x1": [-1, 1, -1, 1, 0, 0, 0, -1.4142, 0, 1.4142, 0],
        "x2": [-1, -1, 1, 1, 0, 0, 0, 0, 1.4142, 0, -1.4142],
    },
    "6A.1-k2-alfa-1,4": {
        "x1": [-1, 1, -1, 1, -1.4, 1.4, 0, 0, 0, 0, 0, 0, 0],
        "x2": [-1, -1, 1, 1, 0, 0, -1.4, 1.4, 0, 0, 0, 0, 0],
    },
    "6A.2-k3": {
        "x1": [-1, 1, -1, 1, -1, 1, -1, 1, -1.682, 1.682] + [0] * 9,
        "x2": [-1, -1, 1, 1, -1, -1, 1, 1, 0, 0, -1.682, 1.682] + [0] * 7,
        "x3": [-1] * 4 + [1] * 4 + [0] * 4 + [-1.682, 1.682] + [0] * 5,
    },
    "6A.3-k4": _colunas_colesterol(),
    "6A.4-k2-duplicatas": {"x1": _LACASE_X1, "x2": _LACASE_X2},
}


@pytest.mark.parametrize("nome", list(_EXEMPLOS_DO_LIVRO))
def test_exemplos_do_livro_sao_reconhecidos_como_dccr(nome: str) -> None:
    """Seção 6.5 (p. 294-297): todos os exemplos do livro são DCCR."""
    from ensaia.core.identificacao import identificar_planejamento

    colunas = _EXEMPLOS_DO_LIVRO[nome]
    assert identificar_planejamento(colunas).tipo == "composto_central"
