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
from dataclasses import dataclass, replace
from typing import Literal

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

Papel = Literal["fator", "resposta", "ignorar"]

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

    Texto é ignorado; uma coluna 1..n com nome de ensaio também (ela não é
    fator nem resposta — vira a sugestão inicial de `ordem_sugerida`, não um
    papel de coluna); a última coluna numérica restante é a resposta; as
    demais numéricas são fatores. O usuário (ou o assistente de IA) corrige o
    que não bater.
    """
    numericas = [
        c
        for c in tabela.colunas
        if tabela.e_numerica(c) and not parece_ordem(c, tabela)
    ]
    ultima = numericas[-1] if numericas else None
    papeis: dict[str, Papel] = {}
    for coluna in tabela.colunas:
        if not tabela.e_numerica(coluna) or parece_ordem(coluna, tabela):
            papeis[coluna] = "ignorar"
        elif coluna == ultima:
            papeis[coluna] = "resposta"
        else:
            papeis[coluna] = "fator"
    return papeis


def ordem_sugerida(tabela: Table) -> list[int] | None:
    """Posto de execução de cada linha (1..n), de uma coluna detectada.

    Usa a mesma coluna que `parece_ordem` reconhece (ex.: "Ensaio", "N",
    "Run"). Informar a ordem de execução é problema de quem desenha e roda o
    experimento, não do EnsaIA — por isso não há tela para digitá-la: `None`
    quando nenhuma coluna bate, e o gráfico de resíduos × ordem (D3) só
    aparece quando bate.
    """
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
) -> AnaliseDaTabela:
    """Reconhece o planejamento, escolhe os termos e roda o núcleo.

    `tipo_modelo=None` deixa o EnsaIA escolher pelo tipo de planejamento.

    `tipo_planejamento`, se dado, força o rótulo do delineamento em vez do
    detectado pela geometria (RF-06): Box-Behnken e um fatorial 3^k, por
    exemplo, têm os mesmos 3 níveis, e a heurística pode escolher errado. Não
    muda a codificação dos fatores (os ±1/α sempre vêm dos níveis reais, em
    `identificar_planejamento`) — só o rótulo e, por tabela, o `tipo_modelo`
    automático e o modelo quadrático/falta de ajuste que dependem dele.

    `coluna_ordem` e `ordem_execucao` são as duas formas de informar a ordem
    de execução (spec §8.3): a primeira lê uma coluna da planilha; a segunda
    (usada pela tela, que deixa arrastar os ensaios) já traz o posto de cada
    linha — ver `postos_da_sequencia`. Dá pra usar uma ou outra, nunca as
    duas; se vierem as duas, `coluna_ordem` tem prioridade.
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
    if tipo_planejamento is not None and tipo_planejamento != planejamento.tipo:
        planejamento = replace(planejamento, tipo=tipo_planejamento)
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
        ordem_execucao=ordem_execucao,
        analises=list(analises) if analises is not None else None,
        objetivos=dict(objetivos) if objetivos is not None else None,
    )
    return AnaliseDaTabela(resultado, planejamento, candidatos)
