"""Estatística descritiva das respostas (A1) e matriz real × codificada (A3).
O primeiro resumo dos dados, antes de qualquer modelo.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ensaia.core.design import Planejamento
from ensaia.core.results import EstatisticaDescritiva
from ensaia.core.table import Table


def estatistica_descritiva(
    tabela: Table, respostas: Sequence[str]
) -> list[EstatisticaDescritiva]:
    """n, média, desvio, mínimo, máximo e CV de cada resposta."""
    resumo: list[EstatisticaDescritiva] = []
    for resposta in respostas:
        y = np.asarray(tabela.coluna(resposta), dtype=float)
        y = y[~np.isnan(y)]
        if y.size == 0:
            continue
        media = float(y.mean())
        desvio = float(y.std(ddof=1)) if y.size > 1 else 0.0
        resumo.append(
            EstatisticaDescritiva(
                resposta=resposta,
                n=int(y.size),
                media=media,
                desvio_padrao=desvio,
                minimo=float(y.min()),
                maximo=float(y.max()),
                cv_percentual=desvio / abs(media) * 100.0 if media != 0 else None,
            )
        )
    return resumo


def matriz_codificada(
    tabela: Table, planejamento: Planejamento
) -> dict[str, list[float]]:
    """Coluna codificada de cada fator, na ordem dos ensaios."""
    return {
        f.nome: [f.codificar(float(v)) for v in tabela.coluna(f.nome)]
        for f in planejamento.fatores
    }


@dataclass(frozen=True)
class MatrizEnsaios:
    """A planilha como o PDF a mostra: valores reais, codificados e respostas."""

    nome_arquivo: str | None
    real: dict[str, list[float]]
    codificada: dict[str, list[float]]
    respostas: dict[str, list[float]]

    @property
    def n_ensaios(self) -> int:
        """Quantos ensaios a matriz tem."""
        return len(next(iter(self.real.values()), []))


def matriz_ensaios(
    tabela: Table,
    planejamento: Planejamento,
    respostas: Sequence[str],
    nome_arquivo: str | None = None,
) -> MatrizEnsaios:
    """Monta a MatrizEnsaios a partir da tabela e do planejamento."""
    return MatrizEnsaios(
        nome_arquivo=nome_arquivo,
        real={
            f.nome: [float(v) for v in tabela.coluna(f.nome)]
            for f in planejamento.fatores
        },
        codificada=matriz_codificada(tabela, planejamento),
        respostas={r: [float(v) for v in tabela.coluna(r)] for r in respostas},
    )
