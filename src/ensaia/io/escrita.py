"""Tabela de volta para CSV: o formato que circula entre as ferramentas do MCP.

Uma planilha .xlsx/.ods lida pelo `read_table` volta como CSV normalizado
(vírgula separando colunas, ponto decimal, UTF-8), para o assistente de IA
repassar os mesmos dados às outras ferramentas sem reler o arquivo.

Células de texto que começam com `=`, `+`, `-` ou `@` ganham um apóstrofo na
frente (spec §15): se o CSV for aberto numa planilha, elas não viram fórmula.
Números nunca são tocados — o `-1` de um nível codificado continua número.
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
    return f"'{texto}" if texto.startswith(_INICIO_DE_FORMULA) else texto
