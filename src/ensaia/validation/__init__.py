"""Validação do EnsaIA contra valores publicados (§4.3 do pré-projeto).
Métricas, fidelidade do texto e o runner dos casos de estudo.
"""

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
