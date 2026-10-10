"""Estado da tela de resultados que os blocos finais compartilham."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ensaia.ai.report import RelatorioTextual
from ensaia.core.results import AnalysisResult


@dataclass
class Sessao:
    """O que os botões finais usam: a análise atual e o último texto mostrado.

    A análise pode ganhar o ponto ótimo depois (bloco "Melhor condição"); por
    isso PDF, JSON e texto leem daqui no momento do clique, não de uma cópia
    capturada quando a tela foi montada. Quem mostra algo derivado da análise
    (o texto sem IA, o pedido para copiar) se inscreve em `ouvintes` para se
    refazer quando ela muda.
    """

    analise: AnalysisResult
    texto: RelatorioTextual | None = None
    # Um ouvinte por bloco: reinscrever com o mesmo nome substitui o anterior.
    ouvintes: dict[str, Callable[[], None]] = field(default_factory=dict)

    def trocar_analise(self, analise: AnalysisResult) -> None:
        self.analise = analise
        for ouvinte in list(self.ouvintes.values()):
            ouvinte()
