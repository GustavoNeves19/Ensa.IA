"""Validação do pipeline contra valores publicados — §4.3 do pré-projeto."""

from ensaia.validation.metrics import (
    comparacao_r2,
    concordancia_significancia,
    diferenca_condicao_otima,
    erro_relativo_coeficientes,
)

__all__ = [
    "comparacao_r2",
    "concordancia_significancia",
    "diferenca_condicao_otima",
    "erro_relativo_coeficientes",
]
