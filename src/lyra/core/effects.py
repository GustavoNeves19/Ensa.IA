"""Coeficientes, efeitos e intervalos de confiança."""

from __future__ import annotations

from lyra.core.results import Coeficiente

ALFA_PADRAO = 0.05


def extrair_coeficientes(
    ajuste,
    *,
    alfa: float = ALFA_PADRAO,
    calcular_ic: bool = True,
) -> list[Coeficiente]:
    """Converte o ajuste OLS na lista de `Coeficiente` do contrato público.

    TODO(#5): implementar. Atenção ao nome dos termos: têm que sair na notação
    canônica de `design.termos_do_modelo` ("x1^2", "x1:x2"), e não na notação
    interna do statsmodels/patsy ("I(x1 ** 2)", "x1:x2"). A comparação do
    §4.3(a) casa coeficientes por nome — divergência de notação vira
    "termo ausente" e estraga a métrica silenciosamente.
    """
    raise NotImplementedError("Ver issue #5 — coeficientes e efeitos.")


def efeitos_principais(coeficientes: list[Coeficiente]) -> dict[str, float]:
    """Efeito de cada fator: em variáveis codificadas, efeito = 2 x coeficiente.

    O fator 2 existe porque o coeficiente mede a variação da resposta ao ir do
    centro (0) até o nível alto (+1), enquanto o efeito mede a variação do
    nível baixo (-1) ao alto (+1). Confundir os dois é um erro comum ao
    comparar com valores publicados — parte da literatura reporta efeito, e
    parte reporta coeficiente.

    TODO(#5): implementar.
    """
    raise NotImplementedError("Ver issue #5 — coeficientes e efeitos.")
