"""Identidade visual do PDF: cores da UFRA, fontes e casas decimais.
Trocar a marca do relatório é mexer só aqui.
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
    """Cores, fontes e medidas do relatório."""

    # Paleta da UFRA: preto, verde-mata e cinzas quentes.
    tinta: Cor = (29, 29, 27)
    acento: Cor = (14, 58, 38)
    cinza: Cor = (94, 90, 78)
    cinza_claro: Cor = (228, 226, 214)
    branco: Cor = (255, 255, 255)

    # Cores dos gráficos, as mesmas da tela.
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

    # Fontes DejaVu embutidas, para acentos e símbolos.
    familia: str = "DejaVu"
    arquivo_regular: Path = field(default=_DIR_FONTES / "DejaVuSans.ttf")
    arquivo_negrito: Path = field(default=_DIR_FONTES / "DejaVuSans-Bold.ttf")
    arquivo_italico: Path = field(default=_DIR_FONTES / "DejaVuSans-Oblique.ttf")

    # Medidas em milímetros (unidade padrão do fpdf2).
    margem: float = 18.0

    # Casas decimais por grandeza.
    casas_p: int = 4
    casas_r2: int = 3
    casas_coef: int = 4


TEMA = Tema()
