"""Núcleo determinístico do EnsaIA.

Regra deste pacote: nada aqui dentro importa a camada de LLM, faz chamada de
rede ou lê variável de ambiente de API. O resultado de `core` tem que ser
idêntico byte a byte entre execuções, na máquina de qualquer pessoa, sem
internet. A fronteira é verificada automaticamente em
tests/test_arquitetura.py.
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
