"""Testes das opções ECharts (ui/graficos): dado do núcleo → dicionário do gráfico.

Não abrem navegador. Conferem o que importa para a leitura: ordem do Pareto,
linha do t crítico, cor por significância, ensaio certo em cada ponto e a grade
da superfície no formato que o ECharts espera.
"""

from __future__ import annotations

import pytest

from ensaia.core.design import Fator, Planejamento, termos_do_modelo
from ensaia.core.diagnostico import pontos_qq
from ensaia.core.pipeline import analisar
from ensaia.core.surface import grade_superficie
from ensaia.core.table import Table
from ensaia.ui import graficos
from ensaia.ui.tema import SERIE, SERIE_APAGADA


def _ajuste():
    x1 = [-1, 1, -1, 1, -1, 1, -1, 1, 0, 0, 0]
    x2 = [-1, -1, 1, 1, -1, -1, 1, 1, 0, 0, 0]
    ruido = [0.3, -0.2, 0.1, -0.4, 0.2, 0.1, -0.3, 0.2, 0.05, -0.1, 0.0]
    y = [
        10 + 4 * a + 0.1 * b + 2 * a * b + e
        for a, b, e in zip(x1, x2, ruido, strict=True)
    ]
    tabela = Table.de_colunas({"temp_reator": x1, "ph": x2, "rend": y})
    plan = Planejamento(
        tipo="desconhecido",
        fatores=[Fator("temp_reator", -1.0, 1.0), Fator("ph", -1.0, 1.0)],
    )
    termos = termos_do_modelo(["temp_reator", "ph"], incluir_quadraticos=False)
    analise = analisar(tabela, plan, termos, ["rend"], versao_ensaia="t")
    return analise.ajustes[0], plan


def test_nome_legivel() -> None:
    assert graficos.nome_legivel("temp_reator:ph") == "temp reator × ph"
    assert graficos.nome_legivel("ph^2") == "ph²"


def test_pareto_ordena_e_marca_o_t_critico() -> None:
    ajuste, _ = _ajuste()
    op = graficos.opcoes_pareto(ajuste, alfa=0.05)
    categorias = op["yAxis"]["data"]
    assert "Intercepto" not in categorias
    assert categorias[0] == "temp reator"  # maior |t| primeiro (eixo invertido)
    sig, nao = op["series"]
    assert sig["itemStyle"]["color"] == SERIE
    assert nao["itemStyle"]["color"] == SERIE_APAGADA
    # Cada termo tem valor em exatamente uma das duas séries.
    for a, b in zip(sig["data"], nao["data"], strict=True):
        assert (a == "-") != (b == "-")
    assert sig["markLine"]["data"] == [{"xAxis": ajuste.t_critico}]
    # Termo de efeito ~0 (ph) fica na série apagada.
    i_ph = categorias.index("ph")
    assert sig["data"][i_ph] == "-"


def test_preditos_observados_leva_o_ensaio_certo() -> None:
    ajuste, _ = _ajuste()
    op = graficos.opcoes_preditos_observados(ajuste)
    pontos = op["series"][0]["data"]
    d = ajuste.diagnostico
    assert len(pontos) == len(d.observados)
    primeiro = pontos[0]
    assert primeiro[0] == pytest.approx(d.observados[0])
    assert primeiro[1] == pytest.approx(d.preditos[0])
    assert primeiro[2] == 1  # número do ensaio, contando de 1
    # Eixos iguais: a reta y = x fica na diagonal de verdade.
    assert op["xAxis"]["min"] == op["yAxis"]["min"]
    assert op["xAxis"]["max"] == op["yAxis"]["max"]


def test_residuos_centrados_no_zero() -> None:
    ajuste, _ = _ajuste()
    op = graficos.opcoes_residuos_preditos(ajuste)
    assert op["yAxis"]["min"] == pytest.approx(-op["yAxis"]["max"])
    assert op["series"][0]["markLine"]["data"] == [{"yAxis": 0}]


def test_qq_usa_os_pontos_do_nucleo() -> None:
    ajuste, _ = _ajuste()
    qq = pontos_qq(ajuste.diagnostico.residuos)
    op = graficos.opcoes_qq(qq)
    dados = op["series"][0]["data"]
    assert [p[1] for p in dados] == qq.amostrais
    assert [p[2] for p in dados] == qq.ensaios


def test_contorno_tem_a_grade_inteira() -> None:
    ajuste, plan = _ajuste()
    grade = grade_superficie(ajuste, plan.fatores, "temp_reator", "ph", pontos=5)
    op = graficos.opcoes_contorno(grade)
    dados = op["series"][0]["data"]
    assert len(dados) == 25
    assert len(op["xAxis"]["data"]) == 5 and len(op["yAxis"]["data"]) == 5
    assert dados[0] == [0, 0, grade.z[0][0]]
    assert op["visualMap"]["min"] <= grade.z_minimo
    assert op["visualMap"]["max"] >= grade.z_maximo


def test_superficie_3d_pede_echarts_gl() -> None:
    ajuste, plan = _ajuste()
    grade = grade_superficie(ajuste, plan.fatores, "temp_reator", "ph", pontos=4)
    op = graficos.opcoes_superficie_3d(grade)
    assert any("3D" in chave for chave in op)  # a NiceGUI liga o echarts-gl por isso
    assert op["series"][0]["type"] == "surface"
    assert len(op["series"][0]["data"]) == 16


def test_graficos_do_fatorial_e_da_ordem() -> None:
    from ensaia.core.fatorial import pontos_meio_normal
    from ensaia.core.termos import escolher_termos
    from tests.unit.test_fatorial_diagnostico import _ajustar, _fatorial_com_centros

    tabela, plan = _fatorial_com_centros()
    sel = escolher_termos(tabela, plan)
    ajuste = _ajustar(tabela, plan, sel)
    ef = ajuste.efeitos_fatorial
    assert ef is not None

    mn = graficos.opcoes_meio_normal(pontos_meio_normal(ef.efeitos), 1.0, {"temp"})
    ativos, ruido = mn["series"]
    assert [p[2] for p in ativos["data"]] == ["temp"]  # só o ativo ganha rótulo
    assert len(ativos["data"]) + len(ruido["data"]) == len(ef.efeitos)
    assert ativos["markLine"]["data"] == [{"xAxis": 1.0}]

    m = ef.medias_principais[0]
    op = graficos.opcoes_medias(m, 0.0, 100.0)
    assert op["series"][0]["data"] == m.medias
    assert (op["yAxis"]["min"], op["yAxis"]["max"]) == (0.0, 100.0)

    inter = graficos.opcoes_interacao(ef.medias_interacoes[0])
    assert len(inter["series"]) == 2  # nível baixo e alto do segundo fator

    ordem = graficos.opcoes_residuos_ordem(ajuste)
    xs = [p[0] for p in ordem["series"][0]["data"]]
    assert xs == sorted(xs)  # na ordem de execução
