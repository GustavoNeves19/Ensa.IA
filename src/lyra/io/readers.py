"""Leitura de dados experimentais (CSV/XLSX)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def ler_dados(caminho: Path | str) -> pd.DataFrame:
    """Carrega dados experimentais de CSV ou Excel.

    TODO(#9): implementar. Cuidados que importam para o público-alvo:
        - CSV brasileiro usa ';' como separador e ',' como decimal
        - detectar o separador em vez de exigir que o usuário saiba qual é
        - ignorar linhas iniciadas por '#' (o template usa isso para comentar)
        - preservar os nomes das colunas como o usuário escreveu, sem
          normalizar: ele precisa reconhecer o próprio dado na tela
    """
    raise NotImplementedError("Ver issue #9 — leitura de dados.")
