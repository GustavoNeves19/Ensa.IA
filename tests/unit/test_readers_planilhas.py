"""Leitura de .xls, .ods e .xlsx com várias abas, formato do CSV e limites."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook

from ensaia.io.readers import (
    MAX_LINHAS,
    formato_csv,
    ler_dados_de_bytes,
    listar_abas,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "planilhas"


def _ods(abas: dict[str, list[list[object]]]) -> bytes:
    from odf.opendocument import OpenDocumentSpreadsheet
    from odf.table import Table, TableCell, TableRow
    from odf.text import P

    doc = OpenDocumentSpreadsheet()
    for nome, linhas in abas.items():
        tabela = Table(name=nome)
        for linha in linhas:
            tr = TableRow()
            for valor in linha:
                if isinstance(valor, int | float):
                    celula = TableCell(valuetype="float", value=valor)
                else:
                    celula = TableCell(valuetype="string")
                celula.addElement(P(text=str(valor)))
                tr.addElement(celula)
            tabela.addElement(tr)
        doc.spreadsheet.addElement(tabela)
    saida = BytesIO()
    doc.save(saida)
    return saida.getvalue()


def test_xls_com_duas_abas() -> None:
    conteudo = (FIXTURES / "duas_abas.xls").read_bytes()
    assert listar_abas(conteudo, "x.xls") == ["Leia-me", "Ensaios"]
    tabela = ler_dados_de_bytes(conteudo, "x.xls", aba="Ensaios")
    assert list(tabela.colunas) == ["Ensaio", "Temperatura", "pH", "Rendimento"]
    assert list(tabela.coluna("Rendimento")) == [61.2, 70.4, 64.9, 79.3, 72.0]
    with pytest.raises(ValueError, match="não existe"):
        ler_dados_de_bytes(conteudo, "x.xls", aba="Outra")


def test_ods_le_numeros_e_escolhe_a_aba() -> None:
    conteudo = _ods(
        {
            "Notas": [["texto qualquer"]],
            "Dados": [["Temperatura", "Rendimento"], [40, 61.5], [60, 72.25]],
        }
    )
    assert listar_abas(conteudo, "x.ods") == ["Notas", "Dados"]
    tabela = ler_dados_de_bytes(conteudo, "x.ods", aba="Dados")
    assert list(tabela.coluna("Rendimento")) == [61.5, 72.25]


def test_xlsx_com_varias_abas() -> None:
    livro = Workbook()
    livro.active.title = "Capa"
    folha = livro.create_sheet("Ensaios")
    folha.append(["x", "y"])
    folha.append([1, 2.5])
    folha.append([2, 3.5])
    saida = BytesIO()
    livro.save(saida)
    conteudo = saida.getvalue()
    assert listar_abas(conteudo, "a.xlsx") == ["Capa", "Ensaios"]
    assert list(ler_dados_de_bytes(conteudo, "a.xlsx", aba="Ensaios").coluna("y")) == [
        2.5,
        3.5,
    ]


def test_formato_csv_brasileiro_e_separador_forcado() -> None:
    conteudo = "temp;rend\n40;61,5\n60;72,25\n".encode("latin-1")
    fmt = formato_csv(conteudo, "a.csv")
    assert fmt is not None
    assert (fmt.separador, fmt.decimal, fmt.codificacao) == (";", ",", "UTF-8")
    assert formato_csv(b"x", "a.xlsx") is None
    # Forçar o separador errado junta o cabeçalho numa coluna só: a escolha manda.
    tabela = ler_dados_de_bytes(conteudo, "a.csv", separador=",")
    assert list(tabela.colunas) == ["temp;rend"]
    certo = ler_dados_de_bytes(conteudo, "a.csv", separador=";")
    assert certo.coluna("rend")[1] == 72.25


def test_texto_nao_tem_abas() -> None:
    assert listar_abas(b"a,b\n1,2\n", "a.csv") == []


def test_limite_de_linhas() -> None:
    linhas = ["x,y"] + [f"{i},{i}" for i in range(MAX_LINHAS + 1)]
    with pytest.raises(ValueError, match="limite"):
        ler_dados_de_bytes("\n".join(linhas).encode(), "grande.csv")


def test_formato_desconhecido() -> None:
    with pytest.raises(ValueError, match="ODS"):
        ler_dados_de_bytes(b"", "dados.pdf")
