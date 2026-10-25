"""Apoio à avaliação manual da fidelidade dos textos da IA (§4.3 e).
Separa afirmações, pré-confere números e gera a planilha para o avaliador.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from ensaia.core.numeros import numero_rastreavel, numeros_no_texto
from ensaia.core.results import AnalysisResult

Classificacao = Literal["correta", "imprecisa", "nao_sustentada", "pendente"]


@dataclass
class Afirmacao:
    """Afirmação do relatório aguardando classificação."""

    indice: int
    texto: str
    numeros_citados: list[float] = field(default_factory=list)
    numeros_encontrados_no_resultado: list[float] = field(default_factory=list)
    numeros_sem_correspondencia: list[float] = field(default_factory=list)
    classificacao: Classificacao = "pendente"
    justificativa: str = ""


@dataclass
class RelatorioFidelidade:
    """Fidelidade global de um relatório."""

    afirmacoes: list[Afirmacao]

    @property
    def total(self) -> int:
        """Número de afirmações."""
        return len(self.afirmacoes)

    @property
    def classificadas(self) -> int:
        """Afirmações já classificadas."""
        return sum(1 for a in self.afirmacoes if a.classificacao != "pendente")

    @property
    def fidelidade_global(self) -> float | None:
        """Proporção de corretas; None se houver pendentes."""
        if self.classificadas < self.total or self.total == 0:
            return None
        corretas = sum(1 for a in self.afirmacoes if a.classificacao == "correta")
        return corretas / self.total

    def contagem(self) -> dict[str, int]:
        """Quantas afirmações em cada classe."""
        contagens = {
            "correta": 0,
            "imprecisa": 0,
            "nao_sustentada": 0,
            "pendente": 0,
        }
        for a in self.afirmacoes:
            contagens[a.classificacao] += 1
        return contagens


def segmentar_afirmacoes(relatorio: str) -> list[Afirmacao]:
    """Quebra o relatório em afirmações, uma por sentença."""
    bruto = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÀÇ])", relatorio.strip())
    afirmacoes: list[Afirmacao] = []
    for i, sentenca in enumerate(s.strip() for s in bruto if s.strip()):
        afirmacoes.append(
            Afirmacao(
                indice=i, texto=sentenca, numeros_citados=numeros_no_texto(sentenca)
            )
        )
    return afirmacoes


def _numeros_do_resultado(resultado: AnalysisResult) -> list[float]:
    """Todos os números que o pipeline produziu."""
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
    """Marca os números de cada afirmação que existem no resultado."""
    afirmacoes = segmentar_afirmacoes(relatorio)
    disponiveis = _numeros_do_resultado(resultado)

    for afirmacao in afirmacoes:
        for numero in afirmacao.numeros_citados:
            if numero_rastreavel(
                numero, disponiveis, tolerancia_relativa=tolerancia_relativa
            ):
                afirmacao.numeros_encontrados_no_resultado.append(numero)
            else:
                afirmacao.numeros_sem_correspondencia.append(numero)

    return RelatorioFidelidade(afirmacoes=afirmacoes)


def exportar_planilha_classificacao(
    relatorio_fidelidade: RelatorioFidelidade,
) -> list[dict[str, object]]:
    """Linhas da planilha de classificação manual."""
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
