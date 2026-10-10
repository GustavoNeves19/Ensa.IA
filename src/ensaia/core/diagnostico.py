"""Diagnóstico dos resíduos: valores por ensaio, normalidade e pontos do Q-Q.

Spec §9, grupos C e D: preditos × observados (C6), resíduos × preditos (D1) e
normalidade dos resíduos com gráfico Q-Q e Shapiro-Wilk (D2). Tudo o que esses
gráficos precisam sai daqui, pronto; a interface e o PDF só desenham.

Por que olhar os resíduos: a ANOVA e os testes t supõem que os erros são
independentes, de variância constante e aproximadamente normais. Um R² alto não
garante nada disso. O padrão dos resíduos é o que mostra se dá para confiar nos
valores-p do modelo.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from ensaia.core.results import Diagnostico

# Abaixo de 3 pontos o Shapiro-Wilk não está definido (scipy recusa).
_MINIMO_SHAPIRO = 3


def diagnosticar(
    observados: NDArray[np.float64],
    preditos: NDArray[np.float64],
    *,
    alfa: float = 0.05,
) -> Diagnostico:
    """Monta o `Diagnostico` de uma resposta a partir de y e ŷ.

    Resíduo é `observado − predito`, na ordem das linhas da planilha. O teste de
    Shapiro-Wilk só roda quando faz sentido: com menos de 3 ensaios ele não
    existe, e com resíduos todos iguais (ajuste exato, R² = 1) o scipy devolve
    W = 1 com aviso — um "normal" que não significa nada. Nesses casos o campo
    fica None e o motivo é registrado. Com o teste feito, normalidade é
    rejeitada quando p < `alfa`.
    """
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

    return Diagnostico(
        observados=[float(v) for v in y],
        preditos=[float(v) for v in y_chapeu],
        residuos=[float(v) for v in residuos],
        shapiro_w=w,
        shapiro_p=p,
        normalidade_rejeitada=None if p is None else p < alfa,
        motivo_sem_shapiro=motivo,
    )


@dataclass(frozen=True)
class PontosQQ:
    """Pontos do gráfico Q-Q normal e a reta de referência.

    `teoricos[i]` é o quantil da normal padrão esperado para o i-ésimo menor
    resíduo, e `amostrais[i]` é esse resíduo. `ensaios[i]` diz de qual linha
    da planilha (contando de 1) ele veio, para a interface poder apontar o
    ensaio ao passar o mouse. A reta passa pelos quartis (como o `qqline` do R):
    pontos longe dela, sobretudo nas pontas, indicam desvio da normalidade.
    """

    teoricos: list[float]
    amostrais: list[float]
    ensaios: list[int]
    reta_intercepto: float
    reta_inclinacao: float


def pontos_qq(residuos: list[float]) -> PontosQQ:
    """Calcula os pontos do Q-Q normal dos resíduos (posições de Blom).

    Posição de plotagem de Blom, `(i − 3/8) / (n + 1/4)`, é a usada pelo
    Minitab e a recomendada para a normal. Com resíduos todos iguais a reta fica
    horizontal (inclinação 0), sem dividir por zero.
    """
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
