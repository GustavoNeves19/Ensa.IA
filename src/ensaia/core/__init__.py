"""Núcleo estatístico determinístico: toda conta do EnsaIA acontece aqui.
Não importa IA, rede nem tela (regra conferida em tests/test_arquitetura.py).
"""

from ensaia.core.results import (
    AjusteResposta,
    AnalysisResult,
    Coeficiente,
    FaltaDeAjuste,
    LinhaAnova,
    MetadadosExecucao,
    PontoOtimo,
)

__all__ = [
    "AjusteResposta",
    "AnalysisResult",
    "Coeficiente",
    "FaltaDeAjuste",
    "LinhaAnova",
    "MetadadosExecucao",
    "PontoOtimo",
]
