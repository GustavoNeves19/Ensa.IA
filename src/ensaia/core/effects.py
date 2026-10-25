"""Coeficientes do modelo, efeitos e intervalos de confiança.
Traduz o ajuste OLS para o contrato público (Coeficiente).
"""

from __future__ import annotations

from scipy import stats

from ensaia.core.design import INTERCEPTO, interpretar_termo
from ensaia.core.model import AjusteOLS
from ensaia.core.results import Coeficiente

ALFA_PADRAO = 0.05


def t_critico(alfa: float, graus_liberdade_residuo: int) -> float | None:
    """Valor de |t| acima do qual um termo é significativo no nível α."""
    if graus_liberdade_residuo <= 0:
        return None
    return float(stats.t.ppf(1.0 - alfa / 2.0, df=graus_liberdade_residuo))


def extrair_coeficientes(
    ajuste: AjusteOLS,
    *,
    alfa: float = ALFA_PADRAO,
    calcular_ic: bool = True,
    qm_erro: float | None = None,
    gl_erro: int | None = None,
) -> list[Coeficiente]:
    """Converte o ajuste OLS na lista de coeficientes do contrato."""
    estimativas = ajuste.coeficientes
    erros, ts, ps = ajuste.estatisticas_t(qm_erro, gl_erro)
    intervalo = (
        ajuste.intervalo_confianca(alfa, qm_erro, gl_erro) if calcular_ic else {}
    )

    return [
        Coeficiente(
            termo=termo,
            estimativa=estimativas[termo],
            erro_padrao=erros[termo],
            valor_t=ts[termo],
            valor_p=ps[termo],
            significativo=ps[termo] < alfa,
            ic_inferior=intervalo[termo][0] if termo in intervalo else None,
            ic_superior=intervalo[termo][1] if termo in intervalo else None,
        )
        # Sem as colunas fixas (blocos): não são termos do estudo nem da equação.
        for termo in ajuste.termos_modelo
    ]


def efeitos_principais(coeficientes: list[Coeficiente]) -> dict[str, float]:
    """Efeito de cada fator (2 × coeficiente linear)."""
    efeitos: dict[str, float] = {}
    for coef in coeficientes:
        if coef.termo == INTERCEPTO:
            continue
        partes = interpretar_termo(coef.termo)
        if len(partes) == 1 and partes[0][1] == 1:
            efeitos[coef.termo] = 2.0 * coef.estimativa
    return efeitos
