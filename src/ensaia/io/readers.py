"""Leitura de dados experimentais (CSV/XLSX), sem pandas.

Devolve uma `Table` (colunas em numpy) — ver ADR 0008 e a seção 8.1 da
especificação. CSV é lido com a biblioteca padrão; Excel com openpyxl em modo
somente leitura (fórmulas e macros nunca são executadas; usa o valor em cache).

A leitura funciona por dois caminhos que compartilham o mesmo parse:

- `ler_dados(caminho)` — a partir de um arquivo em disco, usada pelo pipeline de
  validação (`validation/runner`).
- `ler_dados_de_bytes(conteudo, nome)` — a partir de bytes em memória, usada pela
  interface web, que recebe o upload e **nunca o grava em disco** (princípio P1).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path

from ensaia.core.table import Table

# Extensões aceitas. CSV cobre também TSV e TXT delimitado (o separador é
# detectado); Excel é lido pelo openpyxl (.xlsx; .xls legado depende do ambiente).
_EXTENSOES_CSV = {".csv", ".tsv", ".txt"}
_EXTENSOES_EXCEL = {".xlsx", ".xls"}


def ler_dados(caminho: Path | str) -> Table:
    """Carrega dados experimentais de um arquivo em disco como `Table`."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {arquivo}")
    return ler_dados_de_bytes(arquivo.read_bytes(), arquivo.name)


def ler_dados_de_bytes(conteudo: bytes, nome: str) -> Table:
    """Carrega dados experimentais a partir de bytes em memória como `Table`.

    `nome` é o nome do arquivo (ex.: ``"ensaios.csv"``); sua extensão decide o
    leitor. Detecta CSV separado por vírgula, ponto e vírgula ou tabulação —
    CSVs brasileiros com `;` e vírgula decimal são aceitos sem pré-processamento.
    Linhas iniciadas por `#` são comentários; os nomes das colunas são
    preservados como foram escritos pelo usuário.
    """
    extensao = Path(nome).suffix.lower()
    if extensao in _EXTENSOES_EXCEL:
        cabecalho, linhas = _ler_excel(BytesIO(conteudo), nome)
    elif extensao in _EXTENSOES_CSV:
        cabecalho, linhas = _ler_csv(_decodificar(conteudo, nome), nome)
    else:
        raise ValueError(
            f"Formato {extensao or 'sem extensão'!r} não suportado para "
            "dados experimentais. Use CSV, TSV, TXT, XLSX ou XLS."
        )

    _validar_cabecalho(nome, cabecalho)
    linhas = [linha for linha in linhas if any(str(c).strip() for c in linha)]
    if not linhas:
        raise ValueError(f"O arquivo {nome!r} não contém ensaios.")

    dados: dict[str, list[object]] = {nome_col: [] for nome_col in cabecalho}
    for linha in linhas:
        for j, nome_col in enumerate(cabecalho):
            dados[nome_col].append(linha[j] if j < len(linha) else "")
    return Table.de_colunas(dados)


def _decodificar(conteudo: bytes, nome: str) -> str:
    """Decodifica os bytes do CSV tentando as codificações usuais, em ordem."""
    ultimo_erro: UnicodeDecodeError | None = None
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return conteudo.decode(codificacao)
        except UnicodeDecodeError as erro:
            ultimo_erro = erro
    raise ValueError(
        f"Não foi possível ler {nome!r} como UTF-8 ou Latin-1."
    ) from ultimo_erro


def _validar_cabecalho(nome: str, cabecalho: list[str]) -> None:
    if not cabecalho:
        raise ValueError(f"O arquivo {nome!r} não tem cabeçalho.")
    if any(not str(coluna).strip() for coluna in cabecalho):
        raise ValueError(
            "O arquivo tem uma coluna sem nome. Dê um nome a todas as colunas."
        )
    repetidas = [coluna for coluna in cabecalho if cabecalho.count(coluna) > 1]
    if repetidas:
        raise ValueError(f"O arquivo tem colunas repetidas: {sorted(set(repetidas))}.")


def _ler_csv(conteudo: str, nome: str) -> tuple[list[str], list[Sequence[object]]]:
    """Faz o parse de um CSV já decodificado, detectando o separador."""
    linhas_texto = [
        linha for linha in conteudo.splitlines() if not linha.lstrip().startswith("#")
    ]
    amostra = "\n".join(linhas_texto[:20])
    if not amostra.strip():
        raise ValueError(f"O CSV {nome!r} não contém dados além de comentários.")

    try:
        separador = csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        separador = ","

    linhas = list(csv.reader(linhas_texto, delimiter=separador))
    cabecalho = [c.strip() for c in linhas[0]]
    corpo: list[Sequence[object]] = list(linhas[1:])
    return cabecalho, corpo


def _ler_excel(stream: BytesIO, nome: str) -> tuple[list[str], list[Sequence[object]]]:
    """Lê a primeira aba de um Excel em modo somente leitura."""
    from openpyxl import load_workbook

    planilha = load_workbook(stream, read_only=True, data_only=True)
    aba = planilha.active
    if aba is None:
        raise ValueError(f"O arquivo {nome!r} não tem nenhuma aba.")
    linhas = [list(linha) for linha in aba.iter_rows(values_only=True)]
    planilha.close()
    if not linhas:
        raise ValueError(f"O arquivo {nome!r} não contém ensaios.")
    cabecalho = [str(c).strip() if c is not None else "" for c in linhas[0]]
    corpo: list[Sequence[object]] = [
        ["" if c is None else c for c in linha] for linha in linhas[1:]
    ]
    return cabecalho, corpo
