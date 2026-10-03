"""Leitura de dados experimentais (CSV/XLSX)."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd


def ler_dados(caminho: Path | str) -> pd.DataFrame:
    """Carrega dados experimentais de CSV ou Excel.

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
        dados = pd.read_excel(arquivo)
    elif extensao == ".csv":
        dados = _ler_csv(arquivo)
    else:
        raise ValueError(
            f"Formato {extensao or 'sem extensão'!r} não suportado para "
            "dados experimentais. Use CSV, XLSX ou XLS."
        )

    if dados.empty:
        raise ValueError(f"O arquivo {arquivo.name!r} não contém ensaios.")
    if dados.columns.duplicated().any():
        repetidas = sorted(dados.columns[dados.columns.duplicated()].unique())
        raise ValueError(f"O arquivo tem colunas repetidas: {repetidas}.")
    if any(not str(coluna).strip() for coluna in dados.columns):
        raise ValueError(
            "O arquivo tem uma coluna sem nome. Dê um nome a todas as colunas."
        )

    return dados.dropna(axis=0, how="all").reset_index(drop=True)


def _ler_csv(arquivo: Path) -> pd.DataFrame:
    """Lê CSV com codificação e separador detectados de forma conservadora."""
    ultimo_erro: UnicodeDecodeError | None = None
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

    linhas = [
        linha for linha in conteudo.splitlines() if not linha.lstrip().startswith("#")
    ]
    amostra = "\n".join(linhas[:20])
    if not amostra.strip():
        raise ValueError(
            f"O CSV {arquivo.name!r} não contém dados além de comentários."
        )

    try:
        separador = csv.Sniffer().sniff(amostra, delimiters=",;\t|").delimiter
    except csv.Error:
        separador = ","

    # Em CSV brasileiro o ponto e vírgula evita ambiguidade com a vírgula decimal.
    decimal = "," if separador == ";" else "."
    return pd.read_csv(
        arquivo,
        encoding=codificacao,
        sep=separador,
        decimal=decimal,
        comment="#",
    )
