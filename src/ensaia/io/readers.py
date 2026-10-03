"""Leitura de dados experimentais (CSV/XLSX), sem pandas.

Devolve uma `Table` (colunas em numpy) — ver ADR 0008 e a seção 8.1 da
especificação. CSV é lido com a biblioteca padrão; Excel com openpyxl em modo
somente leitura (fórmulas e macros nunca são executadas; usa o valor em cache).
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from ensaia.core.table import Table


def ler_dados(caminho: Path | str) -> Table:
    """Carrega dados experimentais de CSV ou Excel como `Table`.

    Detecta CSV separado por vírgula, ponto e vírgula ou tabulação. CSVs
    brasileiros com `;` e vírgula decimal são aceitos sem pré-processamento.
    Linhas iniciadas por `#` são comentários e os nomes das colunas são
    preservados como foram escritos pelo usuário.
    """
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo de dados não encontrado: {arquivo}")

    extensao = arquivo.suffix.lower()
    if extensao in {".xlsx", ".xls"}:
        cabecalho, linhas = _ler_excel(arquivo)
    elif extensao == ".csv":
        cabecalho, linhas = _ler_csv(arquivo)
    else:
        raise ValueError(
            f"Formato {extensao or 'sem extensão'!r} não suportado para "
            "dados experimentais. Use CSV, XLSX ou XLS."
        )

    _validar_cabecalho(arquivo, cabecalho)
    linhas = [linha for linha in linhas if any(str(c).strip() for c in linha)]
    if not linhas:
        raise ValueError(f"O arquivo {arquivo.name!r} não contém ensaios.")

    dados: dict[str, list[object]] = {nome: [] for nome in cabecalho}
    for linha in linhas:
        for j, nome in enumerate(cabecalho):
            dados[nome].append(linha[j] if j < len(linha) else "")
    return Table.de_colunas(dados)


def _validar_cabecalho(arquivo: Path, cabecalho: list[str]) -> None:
    if not cabecalho:
        raise ValueError(f"O arquivo {arquivo.name!r} não tem cabeçalho.")
    if any(not str(nome).strip() for nome in cabecalho):
        raise ValueError(
            "O arquivo tem uma coluna sem nome. Dê um nome a todas as colunas."
        )
    vistos = [nome for nome in cabecalho if cabecalho.count(nome) > 1]
    if vistos:
        raise ValueError(f"O arquivo tem colunas repetidas: {sorted(set(vistos))}.")


def _ler_csv(arquivo: Path) -> tuple[list[str], list[Sequence[object]]]:
    """Lê CSV com codificação e separador detectados de forma conservadora."""
    ultimo_erro: UnicodeDecodeError | None = None
    conteudo = ""
    for codificacao in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            conteudo = arquivo.read_text(encoding=codificacao)
            break
        except UnicodeDecodeError as erro:
            ultimo_erro = erro
    else:
        raise ValueError(
            f"Não foi possível ler {arquivo.name!r} como UTF-8 ou Latin-1."
        ) from ultimo_erro

    linhas_texto = [
        linha for linha in conteudo.splitlines() if not linha.lstrip().startswith("#")
    ]
    amostra = "\n".join(linhas_texto[:20])
    if not amostra.strip():
        raise ValueError(
            f"O CSV {arquivo.name!r} não contém dados além de comentários."
        )

    try:
        separador = csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        separador = ","

    linhas = list(csv.reader(linhas_texto, delimiter=separador))
    cabecalho = [c.strip() for c in linhas[0]]
    corpo: list[Sequence[object]] = [linha for linha in linhas[1:]]
    return cabecalho, corpo


def _ler_excel(arquivo: Path) -> tuple[list[str], list[Sequence[object]]]:
    """Lê a primeira aba de um Excel em modo somente leitura."""
    from openpyxl import load_workbook

    planilha = load_workbook(arquivo, read_only=True, data_only=True)
    aba = planilha.active
    if aba is None:
        raise ValueError(f"O arquivo {arquivo.name!r} não tem nenhuma aba.")
    linhas = [list(linha) for linha in aba.iter_rows(values_only=True)]
    planilha.close()
    if not linhas:
        raise ValueError(f"O arquivo {arquivo.name!r} não contém ensaios.")
    cabecalho = [str(c).strip() if c is not None else "" for c in linhas[0]]
    corpo: list[Sequence[object]] = [
        ["" if c is None else c for c in linha] for linha in linhas[1:]
    ]
    return cabecalho, corpo
