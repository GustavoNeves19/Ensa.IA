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
    assert IDS == (
        "A1", "A2", "A3", "B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4",
        "C5", "C6", "D1", "D2", "D3", "D4", "E1", "E2", "E3", "E4", "E5",
    )
    assert {a.grupo for a in CATALOGO} == set(GRUPOS)


def test_dccr_nao_tem_grupo_b_de_triagem() -> None:
    # Só DCCR é reconhecido (ADR 0013): B1/B3/B4/B5, do fatorial de 2 níveis
    # para triagem, ficam permanentemente indisponíveis. B2 (Pareto dos
    # efeitos padronizados) não depende do tipo fatorial e continua disponível.
    disp = disponibilidade(
        _colunas(_dcc(3, 1.682, centrais=3)), n_respostas=1, tem_ordem=False
    )
    for id_ in ("B1", "B3", "B4", "B5"):
        assert disp[id_] == "só para fatorial de 2 níveis"
    assert disp["B2"] is None
    assert disp["C4"] is None  # 3 pontos centrais = réplicas
    assert disp["E3"] is None  # modelo quadrático estimável
    assert disp["E5"] is not None  # uma resposta só
    assert "E3" in padrao(disp) and "B1" not in padrao(disp)


def test_fatorial_puro_tambem_fica_sem_grupo_b() -> None:
    # Um fatorial 2^k puro não é mais um tipo reconhecido (vira
    # "desconhecido"), então o Grupo B de triagem — feito justamente para
    # esse caso — também não se aplica mais. Isto documenta a consequência da
    # restrição a DCCR (ADR 0013), não um comportamento desejado do fatorial.
    vertices = list(itertools.product([-1, 1], repeat=3))
    disp = disponibilidade(
        _colunas(vertices + [(0, 0, 0)] * 3), n_respostas=2, tem_ordem=True
    )
    assert disp["B1"] is not None and disp["B4"] is not None and disp["B5"] is not None
    assert disp["E3"] is not None  # sem estrela axial: não há modelo quadrático


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
