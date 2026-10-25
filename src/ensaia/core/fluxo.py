"""Caminho comum de uma planilha até o resultado, para a tela e o MCP.
Sugere o papel das colunas, reconhece o DCCR, escolhe os termos e roda o núcleo.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from ensaia.core.blocos import ler_blocos
from ensaia.core.design import INTERCEPTO, Planejamento
from ensaia.core.identificacao import identificar_planejamento
from ensaia.core.pipeline import ALFA_PADRAO, analisar
from ensaia.core.results import (
    AnalysisResult,
    Sentido,
    TermoErro,
    TipoModelo,
    TipoPlanejamento,
)
from ensaia.core.table import Table
from ensaia.core.termos import escolher_termos, termos_do_tipo

Papel = Literal["fator", "resposta", "bloco", "ignorar"]

# Nomes usuais da coluna de ordem/número do ensaio (spec §8.3).
_NOME_ORDEM = re.compile(
    r"^(ensaio|ensaios|exp|experimento|run|ordem|corrida|n|n[º°o.]?)\b", re.IGNORECASE
)


# Nomes usuais da coluna de bloco (dia, lote, batelada): ver `core/blocos.py`.
_NOME_BLOCO = re.compile(
    r"^(bloco|blocos|block|blocks|blk|lote|lotes|batch|batelada|dia)\b", re.IGNORECASE
)
# Colunas de índice que planilhas e programas acrescentam.
_NOME_INDICE = re.compile(
    r"^(rownames|row\.?names|unnamed:?\s*0|index|indice|índice|id|linha|row)$",
    re.IGNORECASE,
)


def parece_bloco(coluna: str, tabela: Table) -> bool:
    """Diz se a coluna parece de blocos (nome e 2 a n − 1 valores)."""
    if not _NOME_BLOCO.match(coluna.strip()):
        return False
    valores = (
        [float(v) for v in tabela.coluna(coluna)]
        if tabela.e_numerica(coluna)
        else list(tabela.texto(coluna))
    )
    return 2 <= len(set(valores)) < len(valores)


def parece_indice(coluna: str, tabela: Table) -> bool:
    """Diz se a coluna é numeração de linhas (rownames, id, index)."""
    if not _NOME_INDICE.match(coluna.strip()) or not tabela.e_numerica(coluna):
        return False
    valores = [float(v) for v in tabela.coluna(coluna)]
    return len(set(valores)) == len(valores)


def parece_ordem(coluna: str, tabela: Table) -> bool:
    """Diz se a coluna é a ordem de execução dos ensaios (1..n)."""
    if not _NOME_ORDEM.match(coluna.strip()) or not tabela.e_numerica(coluna):
        return False
    valores = sorted(float(v) for v in tabela.coluna(coluna))
    return valores == [float(i) for i in range(1, len(valores) + 1)]


def sugerir_mapeamento(tabela: Table) -> dict[str, Papel]:
    """Papel sugerido para cada coluna: fator, resposta, bloco ou ignorar."""

    def fora(c: str) -> bool:
        """Diz se a coluna é de ordem ou de índice."""
        return parece_ordem(c, tabela) or parece_indice(c, tabela)

    blocos = [c for c in tabela.colunas if parece_bloco(c, tabela)]
    numericas = [
        c
        for c in tabela.colunas
        if tabela.e_numerica(c) and not fora(c) and c not in blocos
    ]
    ultima = numericas[-1] if numericas else None
    papeis: dict[str, Papel] = {}
    for coluna in tabela.colunas:
        if blocos and coluna == blocos[0]:
            papeis[coluna] = "bloco"  # só um bloco por análise
        elif not tabela.e_numerica(coluna) or fora(coluna) or coluna in blocos:
            papeis[coluna] = "ignorar"
        elif coluna == ultima:
            papeis[coluna] = "resposta"
        else:
            papeis[coluna] = "fator"
    return papeis


def ordem_sugerida(tabela: Table) -> list[int] | None:
    """Posto de execução de cada ensaio, a partir da coluna de ordem."""
    for coluna in tabela.colunas:
        if parece_ordem(coluna, tabela):
            return [int(v) for v in tabela.coluna(coluna)]
    return None


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
    tipo_planejamento: TipoPlanejamento | None = None,
    excluidos: Sequence[str] = (),
    termo_erro: TermoErro = "residuo",
    reduzir: bool = False,
    coluna_ordem: str | None = None,
    ordem_execucao: Sequence[int] | None = None,
    analises: Sequence[str] | None = None,
    objetivos: Mapping[str, Sentido] | None = None,
    coluna_bloco: str | None = None,
) -> AnaliseDaTabela:
    """Reconhece o planejamento, escolhe os termos e roda o núcleo."""
    if not fatores:
        raise ValueError("Marque ao menos um fator (uma coluna que você controlou).")
    if not respostas:
        raise ValueError("Marque ao menos uma resposta (uma coluna que você mediu).")
    identificacao = identificar_planejamento(
        {nome: [float(v) for v in tabela.coluna(nome)] for nome in fatores}
    )
    planejamento = identificacao.planejamento
    if tipo_planejamento is not None and tipo_planejamento != planejamento.tipo:
        planejamento = replace(planejamento, tipo=tipo_planejamento)
    blocos = ler_blocos(tabela, coluna_bloco) if coluna_bloco else None
    selecao = escolher_termos(
        tabela,
        planejamento,
        tipo_modelo=tipo_modelo,
        excluidos=excluidos,
        blocos=blocos,
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
        ordem_execucao=ordem_execucao,
        analises=list(analises) if analises is not None else None,
        objetivos=dict(objetivos) if objetivos is not None else None,
        coluna_bloco=coluna_bloco,
    )
    return AnaliseDaTabela(resultado, planejamento, candidatos)
