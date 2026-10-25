"""Estado compartilhado pelos blocos finais da tela de resultados.
Guarda a análise atual, o texto e a matriz, e avisa quem depende deles.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ensaia.ai.report import RelatorioTextual
from ensaia.core.descritiva import MatrizEnsaios
from ensaia.core.results import AnalysisResult


@dataclass
class Sessao:
    """Análise atual, texto mostrado, matriz dos ensaios e ouvintes."""

    analise: AnalysisResult
    texto: RelatorioTextual | None = None
    # A planilha como o PDF a mostra (A3); o contrato não carrega as células.
    dados: MatrizEnsaios | None = None
    # Um ouvinte por bloco: reinscrever com o mesmo nome substitui o anterior.
    ouvintes: dict[str, Callable[[], None]] = field(default_factory=dict)

    def trocar_analise(self, analise: AnalysisResult) -> None:
        """Troca a análise e avisa os blocos inscritos."""
        self.analise = analise
        for ouvinte in list(self.ouvintes.values()):
            ouvinte()
