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
from ensaia.core.pipeline import ALFA_PADRAO, MAX_RESPOSTAS, analisar
from ensaia.core.results import AnalysisResult, Sentido, TermoErro, TipoModelo
from ensaia.core.table import Table
from ensaia.core.termos import escolher_termos, termos_do_tipo

Papel = Literal["fator", "resposta", "ordem", "ignorar"]

# Nomes usuais da coluna de ordem/número do ensaio (spec §8.3), já com "_" e "-"
# trocados por espaço: "run_std", "RunOrder" e "StdOrder" (do Minitab) entram.
_NOME_ORDEM = re.compile(
    r"^(ensaios?|exp|experimentos?|run|runs|runorder|stdorder|std|ordem|corrida|"
    r"n|n[º°o.]?)\b",
    re.IGNORECASE,
)
# Colunas de controle que o Minitab e o Design-Expert exportam junto da matriz.
_METADADOS = {"centerpt", "pttype", "blocks", "block", "bloco", "blocos"}
# Um fator de planejamento de experimentos tem poucos níveis: 2 no fatorial, 3 no
# Box-Behnken, 5 no composto central (com os axiais). Uma resposta, medida em
# cada ensaio, varia quase sempre de ensaio para ensaio.
_MAX_NIVEIS_FATOR = 5


def _normalizado(coluna: str) -> str:
    return re.sub(r"[_\-\s]+", " ", coluna.strip())


def parece_ordem(coluna: str, tabela: Table) -> bool:
    """Coluna 1..n com nome de ensaio/ordem é a ordem de execução (spec §8.3)."""
    if not _NOME_ORDEM.match(_normalizado(coluna)) or not tabela.e_numerica(coluna):
        return False
    return _e_sequencia(tabela, coluna)


def _e_sequencia(tabela: Table, coluna: str) -> bool:
    valores = sorted(float(v) for v in tabela.coluna(coluna))
    return valores == [float(i) for i in range(1, len(valores) + 1)]


def _e_controle(coluna: str, tabela: Table) -> bool:
    """Coluna que não é fator nem resposta: metadado, constante ou só numeração."""
    if _normalizado(coluna).lower().replace(" ", "") in _METADADOS:
        return True
    valores = set(float(v) for v in tabela.coluna(coluna))
    if len(valores) <= 1:
        return True
    # Uma numeração 1..n sem nome de ordem (ex.: "planejamento") não é fator:
    # fator nenhum tem um nível por ensaio.
    return len(tabela) > _MAX_NIVEIS_FATOR and _e_sequencia(tabela, coluna)


def sugerir_mapeamento(tabela: Table) -> dict[str, Papel]:
    """Papel sugerido de cada coluna: o ponto de partida do passo "mapear".

    - Texto, metadados de software (CenterPt, Blocks), colunas constantes e
      numerações sem nome de ordem são ignorados.
    - Uma coluna 1..n com nome de ensaio ou ordem vira ordem.
    - Coluna numérica com poucos níveis (até 5, e menos níveis que ensaios) é
      fator; as que variam de ensaio a ensaio são respostas.
    - Se nenhuma coluna parecer resposta, a última numérica vira resposta, e se
      nenhuma parecer fator, as demais viram fatores. Respostas além do limite
      da análise (5) começam ignoradas. O usuário corrige o que não bater (ou o
      assistente de IA, pelo MCP).
    """
    papeis: dict[str, Papel] = {}
    candidatas: list[str] = []
    for coluna in tabela.colunas:
        if not tabela.e_numerica(coluna):
            papeis[coluna] = "ignorar"
        elif parece_ordem(coluna, tabela):
            papeis[coluna] = "ordem"
        elif _e_controle(coluna, tabela):
            papeis[coluna] = "ignorar"
        else:
            candidatas.append(coluna)
    limite = min(_MAX_NIVEIS_FATOR, len(tabela) - 1)
    for coluna in candidatas:
        niveis = len(set(float(v) for v in tabela.coluna(coluna)))
        papeis[coluna] = "fator" if niveis <= limite else "resposta"
    sugeridos = [papeis[c] for c in candidatas]
    if candidatas and "resposta" not in sugeridos:
        papeis[candidatas[-1]] = "resposta"
    elif candidatas and "fator" not in sugeridos:
        for coluna in candidatas[:-1]:
            papeis[coluna] = "fator"
    # Dentro do limite da análise (spec §15): as primeiras respostas entram, as
    # demais ficam para o usuário trocar uma a uma.
    respostas = [c for c in candidatas if papeis[c] == "resposta"]
    for coluna in respostas[MAX_RESPOSTAS:]:
        papeis[coluna] = "ignorar"
    return {coluna: papeis[coluna] for coluna in tabela.colunas}


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
