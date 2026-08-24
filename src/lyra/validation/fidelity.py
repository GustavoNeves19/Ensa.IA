"""Fidelidade dos relatórios gerados pelo LLM — §4.3(e) do pré-projeto.

O documento assinado define a avaliação como "checagem manual, item a item",
classificando cada afirmação do relatório em três categorias:

    correta        — reflete fielmente o resultado numérico do pipeline
    imprecisa      — sentido geral correto, mas erro de magnitude ou terminologia
    nao_sustentada — sem correspondência nos dados do pipeline (alucinação)

Este módulo NÃO automatiza esse julgamento. Ele estrutura o trabalho manual:
segmenta o relatório em afirmações, gera a planilha de classificação, e faz
uma pré-checagem puramente aritmética dos números citados no texto contra o
AnalysisResult — para poupar tempo do avaliador humano, não para substituí-lo.

A distinção importa para a defesa: se um LLM classificasse as afirmações de
outro LLM, a métrica de alucinação passaria a depender exatamente da
tecnologia sob teste, e o argumento vira circular. O julgamento final é
humano, e o §4.3(e) foi escrito assim de propósito.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from lyra.core.results import AnalysisResult

Classificacao = Literal["correta", "imprecisa", "nao_sustentada", "pendente"]


@dataclass
class Afirmacao:
    """Uma afirmação isolada extraída do relatório, aguardando classificação."""

    indice: int
    texto: str
    numeros_citados: list[float] = field(default_factory=list)
    numeros_encontrados_no_resultado: list[float] = field(default_factory=list)
    numeros_sem_correspondencia: list[float] = field(default_factory=list)
    classificacao: Classificacao = "pendente"
    justificativa: str = ""


@dataclass
class RelatorioFidelidade:
    """§4.3(e) — fidelidade global de um relatório."""

    afirmacoes: list[Afirmacao]

    @property
    def total(self) -> int:
        return len(self.afirmacoes)

    @property
    def classificadas(self) -> int:
        return sum(1 for a in self.afirmacoes if a.classificacao != "pendente")

    @property
    def fidelidade_global(self) -> float | None:
        """Proporção de afirmações corretas sobre o total.

        Retorna None enquanto houver afirmação pendente: uma fidelidade
        calculada sobre classificação incompleta seria enganosa, e é
        exatamente o tipo de número que acaba citado na monografia sem
        ressalva.
        """
        if self.classificadas < self.total or self.total == 0:
            return None
        corretas = sum(1 for a in self.afirmacoes if a.classificacao == "correta")
        return corretas / self.total

    def contagem(self) -> dict[str, int]:
        contagens = {
            "correta": 0,
            "imprecisa": 0,
            "nao_sustentada": 0,
            "pendente": 0,
        }
        for a in self.afirmacoes:
            contagens[a.classificacao] += 1
        return contagens


# Números em português: 1234,56 · 1.234,56 · 0,85 · 12 · -3,4 · 1.2e-5
_PADRAO_NUMERO = re.compile(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:[.,]\d+)?")


def _para_float(texto: str) -> float | None:
    """Converte um número escrito em português para float."""
    t = texto.strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def segmentar_afirmacoes(relatorio: str) -> list[Afirmacao]:
    """Quebra o relatório em afirmações — uma sentença cada.

    Segmentação por sentença é grosseira de propósito: o avaliador humano
    pode juntar ou dividir itens ao revisar. O objetivo é dar um ponto de
    partida reprodutível, não uma análise linguística.
    """
    bruto = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÀÇ])", relatorio.strip())
    afirmacoes: list[Afirmacao] = []
    for i, sentenca in enumerate(s.strip() for s in bruto if s.strip()):
        numeros = [
            n
            for n in (_para_float(m.group()) for m in _PADRAO_NUMERO.finditer(sentenca))
            if n is not None
        ]
        afirmacoes.append(Afirmacao(indice=i, texto=sentenca, numeros_citados=numeros))
    return afirmacoes


def _numeros_do_resultado(resultado: AnalysisResult) -> list[float]:
    """Todos os números que o pipeline determinístico realmente produziu."""
    numeros: list[float] = []
    for ajuste in resultado.ajustes:
        numeros += [ajuste.r2, ajuste.r2_ajustado, float(ajuste.n_observacoes)]
        for c in ajuste.coeficientes:
            numeros += [c.estimativa, c.erro_padrao, c.valor_t, c.valor_p]
        for linha in ajuste.anova:
            numeros += [linha.soma_quadrados, linha.quadrado_medio]
            numeros += [v for v in (linha.valor_f, linha.valor_p) if v is not None]
        lof = ajuste.falta_de_ajuste
        numeros += [v for v in (lof.valor_f, lof.valor_p) if v is not None]
    if resultado.ponto_otimo is not None:
        numeros += list(resultado.ponto_otimo.coordenadas.values())
        numeros += list(resultado.ponto_otimo.resposta_prevista.values())
        numeros.append(resultado.ponto_otimo.desejabilidade_global)
    return numeros


def prechecar_numeros(
    relatorio: str,
    resultado: AnalysisResult,
    *,
    tolerancia_relativa: float = 0.01,
) -> RelatorioFidelidade:
    """Pré-checagem aritmética: todo número do texto existe no resultado?

    Marca em cada afirmação quais números citados têm correspondência no
    `AnalysisResult` e quais não têm. Um número sem correspondência é
    *candidato* a alucinação — não veredito. Falsos positivos são esperados e
    legítimos: o relatório pode citar corretamente um nível de fator vindo dos
    dados de entrada, arredondar ("aproximadamente 95%"), ou derivar um valor
    por conta ("uma diferença de 12 unidades").

    Nenhuma afirmação sai daqui classificada. A classificação é do avaliador.
    """
    afirmacoes = segmentar_afirmacoes(relatorio)
    disponiveis = _numeros_do_resultado(resultado)

    for afirmacao in afirmacoes:
        for numero in afirmacao.numeros_citados:
            escala = max(abs(numero), 1e-9)
            achou = any(
                abs(numero - d) <= tolerancia_relativa * max(escala, abs(d))
                for d in disponiveis
            )
            if achou:
                afirmacao.numeros_encontrados_no_resultado.append(numero)
            else:
                afirmacao.numeros_sem_correspondencia.append(numero)

    return RelatorioFidelidade(afirmacoes=afirmacoes)


def exportar_planilha_classificacao(
    relatorio_fidelidade: RelatorioFidelidade,
) -> list[dict[str, object]]:
    """Linhas prontas para virar CSV/planilha de classificação manual.

    O avaliador preenche a coluna `classificacao` com correta / imprecisa /
    nao_sustentada e justifica. O arquivo preenchido é o dado bruto do
    §4.3(e) e deve ser versionado junto com o caso de estudo.
    """
    return [
        {
            "indice": a.indice,
            "afirmacao": a.texto,
            "numeros_citados": "; ".join(str(n) for n in a.numeros_citados),
            "numeros_sem_correspondencia": "; ".join(
                str(n) for n in a.numeros_sem_correspondencia
            ),
            "classificacao": "",
            "justificativa": "",
        }
        for a in relatorio_fidelidade.afirmacoes
    ]
