"""Camada de apresentação: o relatório PDF padronizado (spec §13).

Consome o `AnalysisResult` (números) e o `RelatorioTextual` (prosa) e produz um
PDF com fpdf2; os gráficos são renderizados em matplotlib na memória. É a única
camada que desenha — o núcleo e a camada de IA nunca importam daqui.
"""

from __future__ import annotations

from ensaia.report.builder import gerar_pdf

__all__ = ["gerar_pdf"]
