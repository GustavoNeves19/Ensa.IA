"""Gera a planilha-modelo .xlsx de um DCCR de 3 fatores, para baixar.
Tem uma aba para preencher e outra com o guia de preenchimento.
"""

from __future__ import annotations

import itertools
from io import BytesIO

_CABECALHO = ["Ensaio", "Temperatura (°C)", "Tempo (min)", "pH", "Rendimento (%)"]
# DCCR de 3 fatores (8 + 6 axiais + 6 centrais); (centro, passo) por fator.
_ALFA = 1.682
_FATORES = {
    "Temperatura (°C)": (50, 10),
    "Tempo (min)": (20, 10),
    "pH": (6, 1),
}
_DCCR = [
    *itertools.product((-1, 1), repeat=3),
    (-_ALFA, 0, 0), (_ALFA, 0, 0),
    (0, -_ALFA, 0), (0, _ALFA, 0),
    (0, 0, -_ALFA), (0, 0, _ALFA),
    *([(0, 0, 0)] * 6),
]
_GUIA = [
    "Como preencher a planilha do EnsaIA",
    "",
    "1. Uma linha por ensaio e uma coluna por fator ou resposta.",
    "2. A primeira linha tem os nomes das colunas; nenhuma coluna sem nome.",
    "3. Fatores: os valores REAIS usados no laboratório (ex.: 40, 50, 60 °C). "
    "O EnsaIA faz a codificação (−1, 0, +1) sozinho.",
    "4. Pontos centrais repetidos entram como linhas repetidas: são eles que "
    "permitem testar a falta de ajuste.",
    "5. Respostas: o que foi medido em cada ensaio (pode haver mais de uma).",
    "6. A coluna 'Ensaio' (ou 'Ordem') com 1, 2, 3… é opcional e serve para "
    "ver se houve deriva ao longo do tempo.",
    "7. Vírgula ou ponto como decimal, tanto faz. Sem células mescladas e sem "
    "linhas de total.",
    "",
    "Os valores da aba Dados são só um exemplo de formato: troque pelos seus.",
]


def planilha_modelo_xlsx() -> bytes:
    """Arquivo .xlsx da planilha-modelo, em bytes."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    livro = Workbook()
    dados = livro.active
    assert dados is not None
    dados.title = "Dados"
    dados.append(_CABECALHO)
    for celula in dados[1]:
        celula.font = Font(bold=True)
    for i, pontos in enumerate(_DCCR, start=1):
        valores = [
            round(centro + p * passo, 2)
            for (centro, passo), p in zip(_FATORES.values(), pontos, strict=True)
        ]
        dados.append([i, *valores, None])
    for coluna, largura in zip("ABCDE", (8, 18, 13, 6, 16), strict=True):
        dados.column_dimensions[coluna].width = largura

    guia = livro.create_sheet("Como preencher")
    for linha in _GUIA:
        guia.append([linha])
    guia["A1"].font = Font(bold=True, size=13)
    guia.column_dimensions["A"].width = 110

    saida = BytesIO()
    livro.save(saida)
    return saida.getvalue()
