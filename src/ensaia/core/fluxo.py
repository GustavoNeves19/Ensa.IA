"""O caminho de uma planilha até o `AnalysisResult`, igual para todos.

A tela (`ui/analise.py`) e o servidor MCP (`mcp_server/`) fazem a mesma coisa:
sugerem o papel de cada coluna, reconhecem o planejamento pelos próprios dados,
escolhem os termos do modelo e rodam o pipeline. Morar aqui garante que um
assistente de IA, pelo MCP, obtém exatamente os números que o químico vê na
tela — o que é a premissa de "a IA não calcula".
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from ensaia.core.design import INTERCEPTO, Planejamento
from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.pipeline import ALFA_PADRAO, analisar
from ensaia.core.results import AnalysisResult, Sentido, TermoErro, TipoModelo
from ensaia.core.table import Table
from ensaia.core.termos import escolher_termos, termos_do_tipo

Papel = Literal["fator", "resposta", "ordem", "ignorar"]

# Nomes usuais da coluna de ordem/número do ensaio (spec §8.3).
_NOME_ORDEM = re.compile(
    r"^(ensaio|ensaios|exp|experimento|run|ordem|corrida|n|n[º°o.]?)\b", re.IGNORECASE
)


def parece_ordem(coluna: str, tabela: Table) -> bool:
    """Coluna 1..n com nome de ensaio/ordem é a ordem de execução (spec §8.3)."""
    if not _NOME_ORDEM.match(coluna.strip()) or not tabela.e_numerica(coluna):
        return False
    valores = sorted(float(v) for v in tabela.coluna(coluna))
    return valores == [float(i) for i in range(1, len(valores) + 1)]


def sugerir_mapeamento(tabela: Table) -> dict[str, Papel]:
    """Papel sugerido de cada coluna: o ponto de partida do passo "mapear".

    Texto é ignorado; uma coluna 1..n com nome de ensaio vira ordem; a última
    coluna numérica é a resposta; as demais numéricas são fatores. O usuário
    (ou o assistente de IA) corrige o que não bater.
    """
    numericas = [
        c
        for c in tabela.colunas
        if tabela.e_numerica(c) and not parece_ordem(c, tabela)
    ]
    ultima = numericas[-1] if numericas else None
    papeis: dict[str, Papel] = {}
    for coluna in tabela.colunas:
        if not tabela.e_numerica(coluna):
            papeis[coluna] = "ignorar"
        elif parece_ordem(coluna, tabela):
            papeis[coluna] = "ordem"
        elif coluna == ultima:
            papeis[coluna] = "resposta"
        else:
            papeis[coluna] = "fator"
    return papeis


@dataclass(frozen=True)
class AnaliseDaTabela:
    """O resultado e o que a tela ainda precisa para desenhá-lo."""

    resultado: AnalysisResult
    # As faixas reais dos fatores (superfície, previsão de uma condição).
    planejamento: Planejamento
    # Termos que o modelo escolhido admite, para o usuário escolher o que tirar.
    candidatos: list[str]


def analisar_tabela(
    tabela: Table,
    fatores: Sequence[str],
    respostas: Sequence[str],
    *,
    versao_ensaia: str,
    alfa: float = ALFA_PADRAO,
    tipo_modelo: TipoModelo | None = None,
    excluidos: Sequence[str] = (),
    termo_erro: TermoErro = "residuo",
    reduzir: bool = False,
    coluna_ordem: str | None = None,
    analises: Sequence[str] | None = None,
    objetivos: Mapping[str, Sentido] | None = None,
) -> AnaliseDaTabela:
    """Reconhece o planejamento, escolhe os termos e roda o núcleo.

    `tipo_modelo=None` deixa o EnsaIA escolher pelo tipo de planejamento.
    Levanta `ValueError` com mensagem em português quando os dados não servem.
    """
    if not fatores:
        raise ValueError("Marque ao menos um fator (uma coluna que você controlou).")
    if not respostas:
        raise ValueError("Marque ao menos uma resposta (uma coluna que você mediu).")
    identificacao = identificar_planejamento(
        {nome: [float(v) for v in tabela.coluna(nome)] for nome in fatores}
    )
    planejamento = identificacao.planejamento
    selecao = escolher_termos(
        tabela, planejamento, tipo_modelo=tipo_modelo, excluidos=excluidos
    )
    niveis = {f.fator.nome: len(f.niveis) for f in identificacao.fatores}
    candidatos = [
        t for t in termos_do_tipo(niveis, selecao.tipo_modelo) if t != INTERCEPTO
    ]
    resultado = analisar(
        tabela,
        planejamento,
        selecao.termos,
        list(respostas),
        versao_ensaia=versao_ensaia,
        alfa=alfa,
        termo_erro=termo_erro,
        reduzir=reduzir,
        tipo_modelo=selecao.tipo_modelo,
        avisos_planejamento=[*identificacao.avisos, *selecao.avisos],
        coluna_ordem=coluna_ordem,
        analises=list(analises) if analises is not None else None,
        objetivos=dict(objetivos) if objetivos is not None else None,
    )
    return AnaliseDaTabela(resultado, planejamento, candidatos)
