"""Coeficientes, efeitos e intervalos de confiança.

Terceiro item do pipeline prometido no pré-projeto. Este módulo traduz o ajuste
OLS (`AjusteOLS`) para o contrato público `Coeficiente` e calcula os efeitos no
sentido clássico de Yates.

A distinção entre *coeficiente* e *efeito* é a armadilha central aqui, e é o
erro mais citado na literatura pesquisada (`docs/pesquisa/nucleo-estatistico.md`,
seção 3): parte dos artigos reporta o coeficiente (variação do centro ao nível
+1) e parte reporta o efeito (variação do nível −1 ao +1). Em escala codificada
±1 os dois diferem por um fator de 2 — mas só para o efeito principal linear.
"""

from __future__ import annotations

from scipy import stats

from ensaia.core.design import INTERCEPTO, interpretar_termo
from ensaia.core.model import AjusteOLS
from ensaia.core.results import Coeficiente

ALFA_PADRAO = 0.05


def t_critico(alfa: float, graus_liberdade_residuo: int) -> float | None:
    """Limiar de |t| acima do qual um termo é significativo no nível `alfa`.

    É a linha vertical do gráfico de Pareto (spec §9, B2): barra que passa da
    linha ⇔ p < alfa no teste t bilateral, a mesma regra de `significativo` em
    `extrair_coeficientes`. Sem grau de liberdade no resíduo não há teste, e a
    função devolve None em vez de um número sem sentido.
    """
    if graus_liberdade_residuo <= 0:
        return None
    return float(stats.t.ppf(1.0 - alfa / 2.0, df=graus_liberdade_residuo))


def extrair_coeficientes(
    ajuste: AjusteOLS,
    *,
    alfa: float = ALFA_PADRAO,
    calcular_ic: bool = True,
) -> list[Coeficiente]:
    """Converte o ajuste OLS na lista de `Coeficiente` do contrato público.

    Lê os coeficientes, erros, t e p diretamente do `AjusteOLS`, que já os
    expõe com os nomes canônicos de termo via `ajuste.termos`. A ordem de saída
    é a ordem dos termos da matriz do modelo, que é estável e a mesma de
    `design.termos_do_modelo` — a comparação com os valores publicados casa por
    nome, não por posição.

    Com `calcular_ic=False`, `ic_inferior`/`ic_superior` ficam None: útil quando
    o intervalo não vai ser usado.
    """
    estimativas = ajuste.coeficientes
    erros = ajuste.erros_padrao
    ts = ajuste.valores_t
    ps = ajuste.valores_p
    intervalo = ajuste.intervalo_confianca(alfa) if calcular_ic else {}

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
        for termo in ajuste.termos
    ]


def efeitos_principais(coeficientes: list[Coeficiente]) -> dict[str, float]:
    """Efeito de Yates de cada fator: `efeito = 2 × coeficiente`.

    Devolve apenas os **efeitos principais lineares** (um fator, potência 1),
    que são os únicos em que a relação `efeito = 2 × coeficiente` vale. A razão
    do fator 2: o coeficiente mede a variação da resposta do centro (0) ao nível
    alto (+1), enquanto o efeito mede a variação do nível baixo (−1) ao alto
    (+1) — o dobro do caminho, numa escala codificada simétrica ±1.

    O que fica **de fora**, de propósito:

    - **Intercepto:** não é efeito de fator nenhum.
    - **Termos quadráticos** ("x^2"): o fator 2 não se aplica. A variação de
      −1 a +1 de um termo ao quadrado é zero (ambos dão 1), e a curvatura é lida
      pelo próprio coeficiente, não por um "efeito" de Yates.
    - **Interações** ("x1:x2"): embora numericamente a interação de Yates também
      seja 2 × coeficiente em desenho 2 níveis, "efeito principal" por definição
      é de um fator isolado. Interações são relatadas pelo coeficiente, como
      pede a issue #5, para não misturar as duas convenções.

    Pré-condição: os coeficientes vêm de um ajuste em escala codificada ±1 — o
    que o pipeline garante (`matriz_modelo(..., codificar=True)` e os fatores
    com níveis ±1 em `design`). A relação `2 × coeficiente` só é o efeito nessa
    escala; em unidades reais o número não tem esse significado.
    """
    efeitos: dict[str, float] = {}
    for coef in coeficientes:
        if coef.termo == INTERCEPTO:
            continue
        partes = interpretar_termo(coef.termo)
        if len(partes) == 1 and partes[0][1] == 1:
            efeitos[coef.termo] = 2.0 * coef.estimativa
    return efeitos
