"""Catálogo das análises do DCCR (A, C, D, E) e suas pré-condições.
Diz quais análises cabem nos dados e, quando não cabem, o motivo em português.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ensaia.core.identificacao import identificar_planejamento


@dataclass(frozen=True)
class Analise:
    """Uma análise do catálogo: identificador, grupo e nome."""

    id: str
    grupo: str
    nome: str


# Grupo B (fatoriais) fora do escopo DCCR; IDs B1–B5 reservados.
GRUPOS: dict[str, str] = {
    "A": "Dados e planejamento",
    "C": "Modelo e ANOVA",
    "D": "Diagnóstico",
    "E": "Superfície e otimização",
}

CATALOGO: tuple[Analise, ...] = (
    Analise("A1", "A", "Estatística descritiva"),
    Analise("A2", "A", "Identificação do DCCR"),
    Analise("A3", "A", "Matriz real e codificada"),
    Analise("C1", "C", "Ajuste do modelo (coeficientes e Pareto)"),
    Analise("C2", "C", "ANOVA"),
    Analise("C3", "C", "R², R² ajustado e de predição"),
    Analise("C4", "C", "Falta de ajuste"),
    Analise("C5", "C", "Equação do modelo"),
    Analise("C6", "C", "Previsto × observado"),
    Analise("D1", "D", "Resíduos × previsto"),
    Analise("D2", "D", "Normalidade dos resíduos"),
    Analise("D3", "D", "Resíduos × ordem de execução"),
    Analise("D4", "D", "Pontos influentes"),
    Analise("E1", "E", "Superfície de resposta 3D"),
    Analise("E2", "E", "Curvas de contorno"),
    Analise("E3", "E", "Ponto estacionário"),
    Analise("E4", "E", "Otimização de uma resposta"),
    Analise("E5", "E", "Desejabilidade (várias respostas)"),
)
IDS: tuple[str, ...] = tuple(a.id for a in CATALOGO)


def disponibilidade(
    fatores: Mapping[str, Sequence[float]],
    *,
    n_respostas: int,
    tem_ordem: bool,
    blocos: Sequence[str] | None = None,
) -> dict[str, str | None]:
    """Para cada análise, None se dá para fazer ou o motivo de não dar."""
    motivos: dict[str, str | None] = dict.fromkeys(IDS)
    if not fatores:
        return dict.fromkeys(IDS, "escolha ao menos um fator")
    if n_respostas == 0:
        return dict.fromkeys(IDS, "escolha ao menos uma resposta")
    try:
        ident = identificar_planejamento(fatores)
    except ValueError as erro:
        return dict.fromkeys(IDS, str(erro).rstrip("."))

    k = len(fatores)
    n = ident.n_ensaios
    condicoes = len({tuple(col[i] for col in fatores.values()) for i in range(n)})
    tem_replicas = condicoes < n
    n_blocos = len(set(blocos)) if blocos is not None else 1
    tem_replicas_no_bloco = (
        len({(blocos[i], *(col[i] for col in fatores.values())) for i in range(n)}) < n
        if blocos is not None
        else tem_replicas
    )

    if n <= k + 1 + (n_blocos - 1):
        sem_modelo = f"{n} ensaios não bastam nem para o modelo linear"
        for id_ in IDS:
            if id_[0] in "CDE":
                motivos[id_] = sem_modelo

    if not tem_replicas_no_bloco:
        motivos["C4"] = (
            "exige réplicas no mesmo bloco (em geral, pontos centrais repetidos)"
            if blocos is not None and tem_replicas
            else "exige réplicas (em geral, pontos centrais repetidos)"
        )
    if n < 3:
        motivos["D2"] = "exige ao menos 3 ensaios"
    if not tem_ordem:
        motivos["D3"] = "arraste os ensaios para informar a ordem de execução"
    if k < 2:
        for id_ in ("E1", "E2"):
            motivos[id_] = "exige ao menos 2 fatores"
    if ident.tipo != "composto_central":
        motivos["E3"] = "exige modelo quadrático (delineamento composto central)"
    if n_respostas < 2:
        motivos["E5"] = "exige ao menos 2 respostas"

    return {id_: motivos[id_] for id_ in IDS}


def padrao(disponiveis: Mapping[str, str | None]) -> list[str]:
    """Seleção inicial: todas as análises disponíveis."""
    return [id_ for id_, motivo in disponiveis.items() if motivo is None]
