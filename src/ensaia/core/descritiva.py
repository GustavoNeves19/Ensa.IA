"""Estatística descritiva e matriz codificada (spec §9, grupo A).

A1 resume cada resposta antes de qualquer modelo: quanto ela variou entre os
ensaios. Um coeficiente de variação muito baixo, por exemplo, já avisa que os
fatores mexeram pouco na resposta. A3 mostra, lado a lado, os níveis reais e os
codificados que o modelo de fato usa.
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
    """n, média, desvio-padrão amostral, mínimo, máximo e CV de cada resposta.

    O CV (desvio / média × 100) fica None quando a média é zero, onde ele não
    tem sentido.
    """
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
    """Coluna codificada de cada fator, na ordem dos ensaios (A3)."""
    return {
        f.nome: [f.codificar(float(v)) for v in tabela.coluna(f.nome)]
        for f in planejamento.fatores
    }


@dataclass(frozen=True)
class MatrizEnsaios:
    """A planilha do experimento como o PDF a mostra (A3): real, codificada e y.

    O contrato `AnalysisResult` não carrega as células (só os resultados); quem
    tem a planilha na mão (a tela) monta isto e entrega ao relatório.
    """

    nome_arquivo: str | None
    real: dict[str, list[float]]
    codificada: dict[str, list[float]]
    respostas: dict[str, list[float]]

    @property
    def n_ensaios(self) -> int:
        return len(next(iter(self.real.values()), []))


def matriz_ensaios(
    tabela: Table,
    planejamento: Planejamento,
    respostas: Sequence[str],
    nome_arquivo: str | None = None,
) -> MatrizEnsaios:
    """Fatores (reais e codificados) e respostas, na ordem dos ensaios."""
    return MatrizEnsaios(
        nome_arquivo=nome_arquivo,
        real={
            f.nome: [float(v) for v in tabela.coluna(f.nome)]
            for f in planejamento.fatores
        },
        codificada=matriz_codificada(tabela, planejamento),
        respostas={r: [float(v) for v in tabela.coluna(r)] for r in respostas},
    )
