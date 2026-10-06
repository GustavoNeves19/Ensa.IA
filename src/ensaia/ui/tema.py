"""Identidade visual da interface — o ponto único de troca de marca da UI.

A spec (seção 0) deixa a identidade definitiva para depois; aqui vai a primeira
proposta, deliberada e não o visual padrão da NiceGUI. A paleta espelha a do
relatório PDF (`report/theme.py`) — a mesma tinta carvão e o mesmo acento
petróleo — para que a tela e o documento gerado falem a mesma língua.

Trocar a marca inteira é mexer só neste arquivo: as cores entram no tema do
Quasar via `ui.colors` e o fundo da página via CSS.
"""

from __future__ import annotations

from nicegui import ui

# Mesma paleta do report/theme.py, em hexadecimal (o que o Quasar/CSS espera).
TINTA = "#1f2328"  # texto e títulos
ACENTO = "#1a5f6f"  # petróleo — ações e destaques
ACENTO_CLARO = "#2b7e92"
CINZA = "#6e767d"  # texto secundário
FUNDO = "#f7f5f2"  # branco quente e escolhido, não o cinza neutro dos UI kits


def aplicar_tema() -> None:
    """Aplica a paleta da marca ao Quasar e o fundo da página.

    Chamada no início de cada página, antes de montar os elementos.
    """
    ui.colors(primary=ACENTO, secondary=TINTA, accent=ACENTO_CLARO)
    ui.query("body").style(f"background-color: {FUNDO}")
