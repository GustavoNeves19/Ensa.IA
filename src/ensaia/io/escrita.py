"""Converte uma Table de volta em CSV normalizado, usado entre as ferramentas MCP.
Textos que começam com =, +, - ou @ ganham apóstrofo para não virar fórmula.
"""

from __future__ import annotations

import csv
import io

from ensaia.core.table import Table

_INICIO_DE_FORMULA = ("=", "+", "-", "@")


def tabela_para_csv(tabela: Table) -> str:
    """CSV com cabeçalho, vírgula como separador e ponto decimal."""
    saida = io.StringIO()
    escritor = csv.writer(saida, lineterminator="\n")
    escritor.writerow(tabela.colunas)
    colunas = [(tabela.texto(c), tabela.e_numerica(c)) for c in tabela.colunas]
    for i in range(len(tabela)):
        escritor.writerow(
            valores[i] if numerica else _neutralizar(valores[i])
            for valores, numerica in colunas
        )
    return saida.getvalue()


def _neutralizar(texto: str) -> str:
    """Põe um apóstrofo antes de texto que viraria fórmula."""
    return f"'{texto}" if texto.startswith(_INICIO_DE_FORMULA) else texto
