"""Grupo B (efeitos, Lenth, curvatura, médias), D3/D4 e A1."""

from __future__ import annotations

import itertools

import numpy as np
import pytest
from scipy import stats

# Pelo módulo: `teste_curvatura` importada no topo seria coletada como teste.
from ensaia.core import fatorial
from ensaia.core.descritiva import estatistica_descritiva, matriz_codificada
from ensaia.core.design import Fator, Planejamento
from ensaia.core.fatorial import analise_lenth, pontos_meio_normal
from ensaia.core.pipeline import analisar
from ensaia.core.table import Table
from ensaia.core.termos import escolher_termos


def _fatorial_com_centros() -> tuple[Table, Planejamento]:
    """2^3 com 4 pontos centrais em unidades reais; y com efeitos conhecidos."""
    vertices = list(itertools.product([-1, 1], repeat=3))
    pontos = vertices + [(0, 0, 0)] * 4
    ruido = [0.2, -0.1, 0.3, -0.2, 0.1, 0.0, -0.3, 0.1, 0.4, -0.2, 0.1, -0.3]
    y = [
        50 + 6 * a - 2 * b + 0.5 * c + 3 * a * b + e
        for (a, b, c), e in zip(pontos, ruido, strict=True)
    ]
    tabela = Table.de_colunas(
        {
            "temp": [60 + 10 * a for a, _, _ in pontos],
            "tempo": [30 + 5 * b for _, b, _ in pontos],
            "conc": [1 + 0.5 * c for _, _, c in pontos],
            "ordem": list(range(1, len(pontos) + 1)),
            "y": y,
        }
    )
    plan = Planejamento(
        "fatorial_completo",
        [Fator("temp", 50, 70), Fator("tempo", 25, 35), Fator("conc", 0.5, 1.5)],
    )
    return tabela, plan


def _analise():
    tabela, plan = _fatorial_com_centros()
    sel = escolher_termos(tabela, plan)
    return analisar(
        tabela, plan, sel.termos, ["y"], versao_ensaia="t", coluna_ordem="ordem"
    ), sel


def test_fatorial_com_centros_usa_modelo_com_interacoes() -> None:
    _, sel = _analise()
    assert sel.tipo_modelo == "interacoes"
    assert not any(t.endswith("^2") for t in sel.termos)


def test_efeito_e_duas_vezes_o_coeficiente() -> None:
    resultado, _ = _analise()
    ajuste = resultado.ajustes[0]
    ef = ajuste.efeitos_fatorial
    assert ef is not None
    coef = {c.termo: c for c in ajuste.coeficientes}
    for e in ef.efeitos:
        assert e.efeito == pytest.approx(2 * coef[e.termo].estimativa)
        assert e.valor_p == pytest.approx(coef[e.termo].valor_p)
    # Efeito de temp ≈ 2 × 6 = 12; de temp:tempo ≈ 2 × 3 = 6.
    por_termo = {e.termo: e.efeito for e in ef.efeitos}
    assert por_termo["temp"] == pytest.approx(12, abs=0.5)
    assert por_termo["temp:tempo"] == pytest.approx(6, abs=0.5)


def test_medias_por_nivel_e_interacao() -> None:
    resultado, _ = _analise()
    ef = resultado.ajustes[0].efeitos_fatorial
    assert ef is not None
    temp = next(m for m in ef.medias_principais if m.fator == "temp")
    assert temp.niveis == [50.0, 70.0]  # só os vértices, sem o centro
    assert temp.medias[1] - temp.medias[0] == pytest.approx(12, abs=0.5)
    assert len(ef.medias_interacoes) == 3
    ab = next(
        m
        for m in ef.medias_interacoes
        if {m.fator_a, m.fator_b} == {"temp", "tempo"}
    )
    assert len(ab.medias) == 2 and len(ab.medias[0]) == 2


def test_lenth_em_exemplo_feito_a_mao() -> None:
    # |e| = 0,5 1 1 2 2 8 10 → mediana 2 → s0 = 3 → corte 7,5 → mediana 1 → PSE 1,5
    lenth = analise_lenth([10, 1, -1, 2, -2, 0.5, 8])
    assert lenth is not None
    assert lenth.pse == pytest.approx(1.5)
    assert lenth.graus_liberdade == pytest.approx(7 / 3)
    assert lenth.me == pytest.approx(stats.t.ppf(0.975, 7 / 3) * 1.5)
    assert lenth.sme > lenth.me
    assert analise_lenth([1.0, 2.0]) is None


def test_curvatura_feita_a_mao() -> None:
    # Vértices 10, 12, 14, 16 (média 13); centro 16, 17, 15, 16 (média 16).
    codificada = np.array(
        [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, 0], [0, 0], [0, 0], [0, 0]],
        dtype=float,
    )
    y = np.array([10, 12, 14, 16, 16, 17, 15, 16], dtype=float)
    r = fatorial.teste_curvatura(
        codificada, y, alfa=0.05, qm_erro_puro=2 / 3, gl_erro_puro=3
    )
    assert r.aplicavel
    assert r.soma_quadrados == pytest.approx(4 * 4 * 9 / 8)
    assert r.valor_f == pytest.approx(18 / (2 / 3))
    assert r.significativa is True
    sem_centro = fatorial.teste_curvatura(
        codificada[:5], y[:5], alfa=0.05, qm_erro_puro=None, gl_erro_puro=0
    )
    assert not sem_centro.aplicavel


def test_meio_normal_ordena_por_magnitude() -> None:
    resultado, _ = _analise()
    ef = resultado.ajustes[0].efeitos_fatorial
    assert ef is not None
    pontos = pontos_meio_normal(ef.efeitos)
    assert pontos.absolutos == sorted(pontos.absolutos)
    assert pontos.quantis == sorted(pontos.quantis)
    assert pontos.termos[-1] == "temp"  # maior efeito no topo


def test_influencia_e_ordem() -> None:
    resultado, _ = _analise()
    d = resultado.ajustes[0].diagnostico
    assert d is not None
    assert d.ordem == [float(i) for i in range(1, 13)]
    p = len(resultado.ajustes[0].termos_incluidos)
    assert sum(d.alavancagem) == pytest.approx(p)  # traço da matriz chapéu
    i = 0
    h, r = d.alavancagem[i], d.residuos_studentizados[i]
    assert r is not None
    assert d.distancia_cook[i] == pytest.approx(r**2 * h / (p * (1 - h)))


def test_outlier_plantado_e_apontado() -> None:
    tabela, plan = _fatorial_com_centros()
    y = list(tabela.coluna("y"))
    y[2] += 15.0  # ensaio 3 fora do padrão
    colunas = {c: list(tabela.coluna(c)) for c in tabela.colunas}
    tabela = Table.de_colunas({**colunas, "y": y})
    sel = escolher_termos(tabela, plan)
    resultado = analisar(tabela, plan, sel.termos, ["y"], versao_ensaia="t")
    d = resultado.ajustes[0].diagnostico
    assert d is not None
    assert 3 in d.possiveis_outliers or 3 in d.ensaios_influentes


def test_descritiva_e_matriz_codificada() -> None:
    tabela, plan = _fatorial_com_centros()
    (resumo,) = estatistica_descritiva(tabela, ["y"])
    y = np.array(tabela.coluna("y"))
    assert resumo.n == 12
    assert resumo.media == pytest.approx(y.mean())
    assert resumo.desvio_padrao == pytest.approx(y.std(ddof=1))
    assert resumo.cv_percentual == pytest.approx(y.std(ddof=1) / y.mean() * 100)
    cod = matriz_codificada(tabela, plan)
    assert cod["temp"][:2] == [-1.0, -1.0] and cod["temp"][-1] == 0.0


def test_fora_de_fatorial_nao_ha_efeitos() -> None:
    from tests.unit.test_modelo_opcoes import TERMOS, _dccr

    tabela, plan = _dccr()
    r = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t")
    assert r.ajustes[0].efeitos_fatorial is None
    assert r.descritiva[0].resposta == "y"


def test_lenth_so_sem_replicas() -> None:
    resultado, _ = _analise()  # tem 4 pontos centrais = réplicas
    ef = resultado.ajustes[0].efeitos_fatorial
    assert ef is not None and ef.lenth is None
    assert all(e.ativo_lenth is None for e in ef.efeitos)

    tabela, plan = _fatorial_com_centros()
    sem_centro = Table.de_colunas(
        {c: list(tabela.coluna(c))[:8] for c in tabela.colunas}
    )
    sel = escolher_termos(sem_centro, plan)
    r = analisar(sem_centro, plan, sel.termos, ["y"], versao_ensaia="t")
    ef2 = r.ajustes[0].efeitos_fatorial
    assert ef2 is not None and ef2.lenth is not None
    assert any(e.ativo_lenth for e in ef2.efeitos)


def test_fatorial_limpo_nao_gera_influente_falso() -> None:
    resultado, _ = _analise()
    d = resultado.ajustes[0].diagnostico
    assert d is not None
    assert d.ensaios_influentes == []
    assert d.possiveis_outliers == []
