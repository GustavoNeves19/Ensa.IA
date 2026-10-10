"""Identidade visual do relatório PDF — o ponto único de troca de marca.

A spec §13 pede que logo, cores e fonte fiquem isolados aqui, para trocar
quando o nome definitivo do produto sair. A paleta é a **oficial da Ufra**
(Manual de Uso da Marca, 2022): o preto (#1D1D1B) como tinta e um verde-mata
profundo como acento — da mesma família dos dois verdes do logotipo, porém
escurecido para ler bem no papel. É a mesma língua visual da interface web
(`ui/theme` → `ui/tema.py`), com cinzas quentes e a DejaVu Sans (Unicode)
carregando tanto o texto do PDF quanto os rótulos dos gráficos.

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

    # Paleta oficial da Ufra: preto como tinta, verde-mata profundo como acento
    # (a mesma família dos dois verdes do logotipo, escurecido para o papel) e
    # cinzas quentes para hierarquia. Nada de gradiente nem de cor berrante.
    tinta: Cor = (29, 29, 27)
    acento: Cor = (14, 58, 38)
    cinza: Cor = (94, 90, 78)
    cinza_claro: Cor = (228, 226, 214)
    branco: Cor = (255, 255, 255)

    # Cores dos gráficos: as mesmas da tela (ui/tema.py), já validadas para
    # daltonismo e contraste. Série principal (termo significativo, ensaios),
    # série apagada (não significativo), os dois níveis de um fator e a rampa
    # sequencial de tom único da superfície (claro → escuro = menor → maior).
    serie: Cor = (46, 133, 64)
    serie_apagada: Cor = (150, 143, 122)
    nivel_baixo: Cor = (127, 176, 116)
    nivel_alto: Cor = (26, 78, 45)
    grade: Cor = (231, 228, 216)
    rampa: tuple[str, ...] = (
        "#8FBD7D",
        "#6FA96A",
        "#529257",
        "#3B7B47",
        "#28643A",
        "#1A4E2D",
        "#0E3A26",
    )

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
