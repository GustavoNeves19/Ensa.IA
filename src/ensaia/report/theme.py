"""Identidade visual do relatório PDF — o ponto único de troca de marca.

A spec §13 pede que logo, cores e fonte fiquem isolados aqui, para trocar
quando o nome definitivo do produto sair. Por ora é um tema sóbrio e
deliberado (não o visual padrão de nenhuma ferramenta): uma tinta carvão, um
acento petróleo e cinzas neutros, com a DejaVu Sans (Unicode) carregando tanto
o texto do PDF quanto os rótulos dos gráficos — uma só linguagem visual.

As cores são tuplas RGB 0–255 (o que o fpdf2 espera); `cor_mpl` as devolve
normalizadas 0–1 para o matplotlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

Cor = tuple[int, int, int]

_DIR_FONTES = Path(__file__).parent / "fonts"


def cor_mpl(cor: Cor) -> tuple[float, float, float]:
    """Converte uma cor RGB 0–255 para o formato 0–1 do matplotlib."""
    r, g, b = cor
    return (r / 255, g / 255, b / 255)


@dataclass(frozen=True)
class Tema:
    """Cores, fontes e medidas do relatório. Trocar aqui muda o visual inteiro."""

    # Paleta: uma tinta escura, um acento petróleo (escolhido — não o azul
    # padrão), e cinzas para hierarquia. Nada de gradiente nem de cor berrante.
    tinta: Cor = (31, 35, 40)
    acento: Cor = (26, 95, 111)
    cinza: Cor = (110, 118, 125)
    cinza_claro: Cor = (228, 231, 234)
    branco: Cor = (255, 255, 255)

    # Fontes Unicode (DejaVu, livre), embutidas no pacote. A regular e a negrito
    # cobrem acentos do português e os símbolos dos fatos (≥, ², −).
    familia: str = "DejaVu"
    arquivo_regular: Path = field(default=_DIR_FONTES / "DejaVuSans.ttf")
    arquivo_negrito: Path = field(default=_DIR_FONTES / "DejaVuSans-Bold.ttf")
    arquivo_italico: Path = field(default=_DIR_FONTES / "DejaVuSans-Oblique.ttf")

    # Medidas em milímetros (unidade padrão do fpdf2).
    margem: float = 18.0

    # Casas decimais por grandeza (spec §13): p-valores com 4, R² com 3,
    # coeficientes com 4 algarismos — padrão brasileiro (vírgula decimal).
    casas_p: int = 4
    casas_r2: int = 3
    casas_coef: int = 4


TEMA = Tema()
