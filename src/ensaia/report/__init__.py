"""Relatório PDF: monta o documento com fpdf2 e os gráficos com matplotlib.
Só desenha o que o resultado já traz; o núcleo e a IA não importam daqui.
"""

from __future__ import annotations

from ensaia.report.builder import gerar_pdf

__all__ = ["gerar_pdf"]
