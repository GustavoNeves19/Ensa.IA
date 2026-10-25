"""Diagnóstico dos resíduos: valores por ensaio, normalidade, Q-Q e influência.
Diz se dá para confiar nos p-valores do modelo (C6, D1, D2, D4).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from ensaia.core.results import Diagnostico

# Abaixo de 3 pontos o Shapiro-Wilk não está definido (scipy recusa).
_MINIMO_SHAPIRO = 3


# Influente: Cook > 1 e hᵢᵢ > 2p/n; outlier: |R-student| > 3.
COOK_INFLUENTE = 1.0
STUDENTIZADO_OUTLIER = 3.0


def diagnosticar(
    observados: NDArray[np.float64],
    preditos: NDArray[np.float64],
    *,
    alfa: float = 0.05,
    alavancagem: NDArray[np.float64] | None = None,
    n_parametros: int | None = None,
    ordem: list[float] | None = None,
) -> Diagnostico:
    """Monta o diagnóstico de uma resposta: resíduos, Shapiro-Wilk e influência."""
    y = np.asarray(observados, dtype=float)
    y_chapeu = np.asarray(preditos, dtype=float)
    if y.shape != y_chapeu.shape:
        raise ValueError(
            f"Observados ({y.shape[0]}) e preditos ({y_chapeu.shape[0]}) têm "
            "tamanhos diferentes."
        )
    residuos = y - y_chapeu

    w: float | None = None
    p: float | None = None
    motivo: str | None = None
    escala = max(1.0, float(np.abs(y).max())) if y.size else 1.0
    if y.size < _MINIMO_SHAPIRO:
        motivo = f"o teste exige ao menos {_MINIMO_SHAPIRO} ensaios"
    elif float(np.ptp(residuos)) <= 1e-12 * escala:
        motivo = "os resíduos são todos iguais (o modelo passa exatamente pelos dados)"
    else:
        resultado = stats.shapiro(residuos)
        w, p = float(resultado.statistic), float(resultado.pvalue)

    diagnostico = Diagnostico(
        observados=[float(v) for v in y],
        preditos=[float(v) for v in y_chapeu],
        residuos=[float(v) for v in residuos],
        shapiro_w=w,
        shapiro_p=p,
        normalidade_rejeitada=None if p is None else p < alfa,
        motivo_sem_shapiro=motivo,
        ordem=list(ordem) if ordem is not None else None,
    )
    return diagnostico.model_copy(
        update=_influencia(residuos, alavancagem, n_parametros)
    )


def _influencia(
    residuos: NDArray[np.float64],
    alavancagem: NDArray[np.float64] | None,
    n_parametros: int | None,
) -> dict[str, object]:
    """Resíduos studentizados, distância de Cook e ensaios a conferir."""
    if alavancagem is None or n_parametros is None:
        return {}
    n = residuos.size
    gl = n - n_parametros
    qm = float(residuos @ residuos) / gl if gl > 0 else 0.0
    studentizados: list[float | None] = []
    externos: list[float | None] = []
    cook: list[float | None] = []
    for e, h in zip(residuos, alavancagem, strict=True):
        folga = 1.0 - float(h)
        if folga < 1e-10 or qm <= 0.0:
            studentizados.append(None)
            externos.append(None)
            cook.append(None)
            continue
        r = float(e) / np.sqrt(qm * folga)
        studentizados.append(float(r))
        cook.append(float(r**2 * h / (n_parametros * folga)))
        # R-student: tᵢ = rᵢ·√((n − p − 1) / (n − p − rᵢ²))
        resto = gl - r**2
        externos.append(
            float(r * np.sqrt((gl - 1) / resto)) if gl > 1 and resto > 1e-12 else None
        )
    corte_h = 2.0 * n_parametros / n
    return {
        "alavancagem": [float(h) for h in alavancagem],
        "residuos_studentizados": studentizados,
        "distancia_cook": cook,
        "ensaios_influentes": [
            i + 1
            for i, (d, h) in enumerate(zip(cook, alavancagem, strict=True))
            if d is not None and d > COOK_INFLUENTE and float(h) > corte_h
        ],
        "possiveis_outliers": [
            i + 1
            for i, t in enumerate(externos)
            if t is not None and abs(t) > STUDENTIZADO_OUTLIER
        ],
    }


@dataclass(frozen=True)
class PontosQQ:
    """Pontos do gráfico Q-Q normal e a reta de referência."""

    teoricos: list[float]
    amostrais: list[float]
    ensaios: list[int]
    reta_intercepto: float
    reta_inclinacao: float


def pontos_qq(residuos: list[float]) -> PontosQQ:
    """Calcula os pontos do Q-Q normal dos resíduos (posições de Blom)."""
    r = np.asarray(residuos, dtype=float)
    n = r.size
    if n == 0:
        return PontosQQ([], [], [], 0.0, 0.0)
    ordem = np.argsort(r, kind="stable")
    amostrais = r[ordem]
    posicoes = (np.arange(1, n + 1) - 0.375) / (n + 0.25)
    teoricos = stats.norm.ppf(posicoes)

    x1, x2 = stats.norm.ppf([0.25, 0.75])
    y1, y2 = np.quantile(r, [0.25, 0.75])
    inclinacao = float((y2 - y1) / (x2 - x1))
    intercepto = float(y1 - inclinacao * x1)

    return PontosQQ(
        teoricos=[float(v) for v in teoricos],
        amostrais=[float(v) for v in amostrais],
        ensaios=[int(i) + 1 for i in ordem],
        reta_intercepto=intercepto,
        reta_inclinacao=inclinacao,
    )
