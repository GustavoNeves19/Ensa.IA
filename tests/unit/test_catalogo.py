"""Catálogo de análises: o que fica disponível em cada planejamento."""

from __future__ import annotations

import itertools
from pathlib import Path

from ensaia.core.catalogo import CATALOGO, GRUPOS, IDS, disponibilidade, padrao
from ensaia.io.readers import ler_dados

CASOS = Path(__file__).resolve().parents[2] / "casos_de_estudo"


def _colunas(pontos: list[tuple[float, ...]]) -> dict[str, list[float]]:
    return {"abc"[j]: [float(p[j]) for p in pontos] for j in range(len(pontos[0]))}


def test_catalogo_cobre_a_spec() -> None:
    assert IDS == (
        "A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4",
        "C5", "C6", "D1", "D2", "D3", "D4", "E1", "E2", "E3", "E4", "E5",
    )
    assert {a.grupo for a in CATALOGO} == set(GRUPOS)


def test_box_behnken_com_replicas_no_centro() -> None:
    dados = ler_dados(CASOS / "mazloomi-2023-zif67-metronidazol" / "dados.csv")
    fatores = {f: list(dados.coluna(f)) for f in list(dados.colunas)[:3]}
    disp = disponibilidade(fatores, n_respostas=1, tem_ordem=False)
    for id_ in ("B1", "B3", "B4", "B5"):
        assert disp[id_] == "só para fatorial de 2 níveis"
    assert disp["C4"] is None  # 3 pontos centrais = réplicas
    assert disp["E3"] is None  # quadrático
    assert disp["D3"] is not None and "ordem" in disp["D3"]
    assert disp["E5"] is not None  # uma resposta só
    assert "E3" in padrao(disp) and "B1" not in padrao(disp)


def test_fatorial_com_e_sem_pontos_centrais() -> None:
    vertices = list(itertools.product([-1, 1], repeat=3))
    com = disponibilidade(
        _colunas(vertices + [(0, 0, 0)] * 3), n_respostas=2, tem_ordem=True
    )
    assert com["B1"] is None and com["B4"] is None and com["B5"] is None
    assert com["B3"] is not None  # há réplicas: Lenth não se aplica
    assert com["E3"] is not None  # sem modelo quadrático
    assert com["D3"] is None and com["E5"] is None

    sem = disponibilidade(_colunas(vertices), n_respostas=1, tem_ordem=False)
    assert sem["B3"] is None  # sem réplicas: é o caso do Lenth
    assert sem["B5"] is not None and sem["C4"] is not None


def test_sem_fator_ou_sem_resposta() -> None:
    assert set(disponibilidade({}, n_respostas=1, tem_ordem=False).values()) == {
        "escolha ao menos um fator"
    }
    disp = disponibilidade({"a": [1.0, 2.0]}, n_respostas=0, tem_ordem=False)
    assert all(m == "escolha ao menos uma resposta" for m in disp.values())


def test_fator_constante_explica_o_motivo() -> None:
    disp = disponibilidade({"a": [5.0, 5.0, 5.0]}, n_respostas=1, tem_ordem=False)
    assert all(m is not None and "não varia" in m for m in disp.values())


def test_pipeline_registra_as_analises_marcadas() -> None:
    import pytest

    from ensaia.core.pipeline import analisar
    from tests.unit.test_modelo_opcoes import TERMOS, _dccr

    tabela, plan = _dccr()
    todas = analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t")
    assert todas.metadados.analises == list(IDS)
    algumas = analisar(
        tabela, plan, TERMOS, ["y"], versao_ensaia="t", analises=["C1", "C2"]
    )
    assert algumas.metadados.analises == ["C1", "C2"]
    with pytest.raises(ValueError, match="desconhecidas"):
        analisar(tabela, plan, TERMOS, ["y"], versao_ensaia="t", analises=["Z9"])
