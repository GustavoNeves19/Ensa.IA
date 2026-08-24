"""Construção da matriz de modelo e ajuste por mínimos quadrados (OLS).

Segundo objetivo específico do pré-projeto: "Apresentar um pipeline
estatístico determinístico que reproduza as etapas fundamentais de uma análise
de DOE, tais como: regressão OLS, ANOVA, cálculo de efeitos e otimização por
função de desejabilidade, utilizando programas em Python."

Este módulo cobre a parte de OLS. Ele NÃO decide quais termos ficam no modelo
final — isso é seleção por significância e vive em `anova.py`, porque depende
da tabela de ANOVA.
"""

from __future__ import annotations

import pandas as pd

from lyra.core.design import Planejamento


def matriz_modelo(
    dados: pd.DataFrame,
    planejamento: Planejamento,
    termos: list[str],
    *,
    codificar: bool = True,
) -> pd.DataFrame:
    """Monta a matriz X do modelo a partir dos termos em notação canônica.

    Trabalhar em variáveis codificadas [-1, +1] não é preciosismo: em unidades
    reais, os termos quadráticos e de interação ficam fortemente
    correlacionados com os lineares, o que infla os erros-padrão e faz
    coeficientes verdadeiros parecerem não significativos. Praticamente toda a
    literatura de DOE reporta coeficientes codificados — e é contra esses
    valores que a validação do §4.3(a) vai comparar.

    TODO(#3): implementar. Para cada termo:
        "Intercepto"  -> coluna de 1s
        "x"           -> coluna codificada do fator x
        "x^2"         -> quadrado da coluna codificada
        "x:y"         -> produto das colunas codificadas
    """
    raise NotImplementedError("Ver issue #3 — implementação do núcleo OLS.")


def ajustar_ols(
    X: pd.DataFrame,
    y: pd.Series,
) -> AjusteOLS:
    """Ajusta y = Xβ + ε por mínimos quadrados ordinários.

    TODO(#3): usar statsmodels.OLS. Guardar o objeto de resultado inteiro —
    a ANOVA e o teste de falta de ajuste precisam dos resíduos e da matriz de
    covariância, não só dos coeficientes.

    Antes de ajustar, verificar o posto de X: se X for posto-deficiente, o
    ajuste "funciona" e devolve coeficientes sem sentido. Falhar alto aqui
    com mensagem clara é melhor que produzir um relatório bonito e errado —
    e um relatório bonito e errado é exatamente o risco que este TCC precisa
    demonstrar que sabe evitar.
    """
    raise NotImplementedError("Ver issue #3 — implementação do núcleo OLS.")


class AjusteOLS:
    """Envelope fino sobre o resultado do statsmodels.

    Existe para que o resto do LYRA não importe statsmodels diretamente: se um
    dia a implementação mudar, muda aqui e em nenhum outro lugar.

    TODO(#3): implementar.
    """
