"""Planilha-modelo para baixar (US-02): o formato certo, com um guia curto.

Gerada em memória com o openpyxl (já é dependência), em duas abas: "Dados",
pronta para preencher, e "Como preencher", com as regras que evitam os erros
mais comuns de quem está começando.
"""

from __future__ import annotations

from io import BytesIO

_CABECALHO = ["Ensaio", "Temperatura (°C)", "Tempo (min)", "pH", "Rendimento (%)"]
# Um Box-Behnken de 3 fatores (15 ensaios, 3 no centro), só nos níveis reais.
_NIVEIS = {
    "Temperatura (°C)": (40, 50, 60),
    "Tempo (min)": (10, 20, 30),
    "pH": (5, 6, 7),
}
_BBD = [
    (-1, -1, 0), (1, -1, 0), (-1, 1, 0), (1, 1, 0),
    (-1, 0, -1), (1, 0, -1), (-1, 0, 1), (1, 0, 1),
    (0, -1, -1), (0, 1, -1), (0, -1, 1), (0, 1, 1),
    (0, 0, 0), (0, 0, 0), (0, 0, 0),
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
    """O arquivo .xlsx da planilha-modelo, em bytes."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    livro = Workbook()
    dados = livro.active
    assert dados is not None
    dados.title = "Dados"
    dados.append(_CABECALHO)
    for celula in dados[1]:
        celula.font = Font(bold=True)
    fatores = list(_NIVEIS)
    for i, pontos in enumerate(_BBD, start=1):
        valores = [_NIVEIS[f][p + 1] for f, p in zip(fatores, pontos, strict=True)]
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
