"""Estatística descritiva e matriz codificada (spec §9, grupo A).

A1 resume cada resposta antes de qualquer modelo: quanto ela variou entre os
ensaios. Um coeficiente de variação muito baixo, por exemplo, já avisa que os
fatores mexeram pouco na resposta. A3 mostra, lado a lado, os níveis reais e os
codificados que o modelo de fato usa.
"""

from __future__ import annotations

from collections.abc import Sequence

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
