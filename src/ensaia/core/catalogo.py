"""Catálogo das análises e suas pré-condições (spec §9 e §4, passo 4).

Cada análise tem um identificador (A1…E5), um grupo e uma pré-condição. A tela
mostra as compatíveis já marcadas e as incompatíveis desabilitadas, com o
motivo em português — "falta de ajuste exige réplicas", por exemplo — em vez de
deixar o usuário marcar algo que não pode ser feito com os dados dele.

O núcleo calcula tudo o que é barato de uma vez; a seleção decide o que aparece
na tela, no PDF e no texto (RF-07, RF-11).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ensaia.core.identificacao import identificar_planejamento

FATORIAIS_2_NIVEIS = ("fatorial_completo", "fatorial_fracionado")


@dataclass(frozen=True)
class Analise:
    id: str
    grupo: str
    nome: str


GRUPOS: dict[str, str] = {
    "A": "Dados e planejamento",
    "B": "Fatoriais (triagem)",
    "C": "Modelo e ANOVA",
    "D": "Diagnóstico",
    "E": "Superfície e otimização",
}

CATALOGO: tuple[Analise, ...] = (
    Analise("A1", "A", "Estatística descritiva"),
    Analise("A2", "A", "Identificação do planejamento"),
    Analise("A3", "A", "Matriz real e codificada"),
    Analise("B1", "B", "Efeitos principais e interações"),
    Analise("B2", "B", "Pareto dos efeitos padronizados"),
    Analise("B3", "B", "Gráfico meio-normal (Lenth)"),
    Analise("B4", "B", "Gráficos de efeito e de interação"),
    Analise("B5", "B", "Teste de curvatura"),
    Analise("C1", "C", "Ajuste do modelo (coeficientes)"),
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
) -> dict[str, str | None]:
    """Para cada análise: None se dá para fazer, ou o motivo (pt-BR) se não dá.

    `fatores` são as colunas mapeadas como fator, na ordem dos ensaios. A
    identificação do planejamento roda aqui mesmo (é barata), para que a tela
    possa atualizar as caixas a cada mudança no mapeamento.
    """
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
    fatorial = ident.tipo in FATORIAIS_2_NIVEIS
    niveis = [len(f.niveis) for f in ident.fatores]

    if n <= k + 1:
        sem_modelo = f"{n} ensaios não bastam nem para o modelo linear"
        for id_ in IDS:
            if id_[0] in "CDE" or id_ in ("B1", "B2", "B3", "B4"):
                motivos[id_] = sem_modelo

    if not fatorial:
        for id_ in ("B1", "B3", "B4", "B5"):
            motivos[id_] = "só para fatorial de 2 níveis"
    else:
        if tem_replicas:
            motivos["B3"] = (
                "com réplicas o erro é estimado direto (use o Pareto); Lenth é "
                "para fatorial sem réplicas"
            )
        if ident.n_pontos_centrais < 2:
            motivos["B5"] = "exige ao menos 2 ensaios no ponto central"

    if not tem_replicas:
        motivos["C4"] = "exige réplicas (em geral, pontos centrais repetidos)"
    if n < 3:
        motivos["D2"] = "exige ao menos 3 ensaios"
    if not tem_ordem:
        motivos["D3"] = (
            "arraste a coluna com a ordem de execução para Ordem dos ensaios"
        )
    if k < 2:
        for id_ in ("E1", "E2"):
            motivos[id_] = "exige ao menos 2 fatores"
    if fatorial or min(niveis) < 3:
        motivos["E3"] = "exige modelo quadrático (3 ou mais níveis por fator)"
    if n_respostas < 2:
        motivos["E5"] = "exige ao menos 2 respostas"

    return {id_: motivos[id_] for id_ in IDS}


def padrao(disponiveis: Mapping[str, str | None]) -> list[str]:
    """Seleção inicial: todas as análises compatíveis (spec §4, passo 4)."""
    return [id_ for id_, motivo in disponiveis.items() if motivo is None]
