"""Catálogo de análises: o que fica disponível em cada planejamento."""

from __future__ import annotations

import itertools

from ensaia.core.catalogo import CATALOGO, GRUPOS, IDS, disponibilidade, padrao


def _colunas(pontos: list[tuple[float, ...]]) -> dict[str, list[float]]:
    return {"abc"[j]: [float(p[j]) for p in pontos] for j in range(len(pontos[0]))}


def _dcc(k: int, alfa: float, centrais: int) -> list[tuple[float, ...]]:
    estrela = []
    for j in range(k):
        for s in (-alfa, alfa):
            p = [0.0] * k
            p[j] = s
            estrela.append(tuple(p))
    vertices = list(itertools.product([-1.0, 1.0], repeat=k))
    return vertices + estrela + [tuple([0.0] * k)] * centrais


def test_catalogo_cobre_a_spec() -> None:
    # Spec v0.6 §9: só os grupos A, C, D e E. B1–B5 (fatoriais de triagem)
    # ficam reservados para a versão geral e não aparecem no catálogo.
    assert IDS == (
        "A1", "A2", "A3", "C1", "C2", "C3", "C4", "C5", "C6",
        "D1", "D2", "D3", "D4", "E1", "E2", "E3", "E4", "E5",
    )
    assert set(GRUPOS) == {"A", "C", "D", "E"}
    assert {a.grupo for a in CATALOGO} == set(GRUPOS)


def test_dccr_tem_todas_as_analises_de_uma_resposta() -> None:
    disp = disponibilidade(
        _colunas(_dcc(3, 1.682, centrais=3)), n_respostas=1, tem_ordem=False
    )
    assert disp["C1"] is None  # coeficientes e Pareto
    assert disp["C4"] is None  # 3 pontos centrais = réplicas
    assert disp["E3"] is None  # modelo quadrático estimável
    assert disp["E5"] is not None  # uma resposta só
    assert disp["D3"] is not None  # sem coluna de ordem
    assert "E3" in padrao(disp)


def test_fatorial_puro_nao_e_dccr() -> None:
    # Um fatorial 2^k puro não é DCCR (ADR 0013): sem estrela axial não há
    # modelo quadrático nem ponto estacionário.
    vertices = list(itertools.product([-1, 1], repeat=3))
    disp = disponibilidade(
        _colunas(vertices + [(0, 0, 0)] * 3), n_respostas=2, tem_ordem=True
    )
    assert disp["E3"] is not None


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
