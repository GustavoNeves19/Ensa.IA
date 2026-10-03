"""Tabela de ANOVA, seleção de termos e teste de falta de ajuste.

Critério de significância: alfa = 0,05, conforme §4.3(b) do pré-projeto
assinado. O protótipo original usava p <= 0,10; a mudança é deliberada e está
registrada em docs/decisoes/0003-criterio-de-significancia.md.
"""

from __future__ import annotations

import pandas as pd

from ensaia.core.results import FaltaDeAjuste, LinhaAnova

ALFA_PADRAO = 0.05


def tabela_anova(ajuste, tipo: int = 2) -> list[LinhaAnova]:
    """Constrói a tabela de ANOVA do modelo ajustado.

    ANOVA tipo II por padrão: com planejamentos desbalanceados (o que acontece
    sempre que há pontos centrais repetidos), a soma de quadrados sequencial
    (tipo I) depende da ordem em que os termos entram no modelo, e resultados
    que mudam conforme a ordem das colunas não são defensáveis numa banca.

    TODO(#4): a Tipo II já é calculada em numpy por `AjusteOLS.tabela_tipo2()`
    (ver model.py e ADR 0007); aqui é só adaptá-la para `list[LinhaAnova]` e
    acrescentar a decomposição falta de ajuste/erro puro. Sem statsmodels.
    """
    raise NotImplementedError("Ver issue #4 — ANOVA e seleção de termos.")


def selecionar_termos(
    anova: list[LinhaAnova],
    *,
    alfa: float = ALFA_PADRAO,
    manter_hierarquia: bool = True,
) -> tuple[list[str], list[str]]:
    """Separa os termos em (mantidos, descartados) por significância.

    `manter_hierarquia=True` preserva o princípio hierárquico: se x1:x2 é
    significativo, x1 e x2 ficam no modelo mesmo que individualmente não
    sejam. Modelo não hierárquico deixa de ser invariante à mudança de escala
    dos fatores — os coeficientes passam a depender de onde você pôs o zero, o
    que é indefensável em quimiometria.

    TODO(#4): implementar.
    """
    raise NotImplementedError("Ver issue #4 — ANOVA e seleção de termos.")


def teste_falta_ajuste(
    dados: pd.DataFrame,
    ajuste,
    fatores: list[str],
) -> FaltaDeAjuste:
    """Decompõe o resíduo em falta de ajuste + erro puro.

    Só é possível com repetições genuínas de uma mesma condição experimental
    (na prática, os pontos centrais). Sem elas, devolver
    `FaltaDeAjuste(aplicavel=False, motivo_inaplicavel=...)` — nunca inventar
    um teste. A camada narrativa depende dessa distinção para não escrever
    "não houve falta de ajuste" quando na verdade o teste não pôde ser feito.

    TODO(#4): implementar.
        1. agrupar linhas por combinação idêntica de níveis dos fatores
        2. SQ_erro_puro = soma dos desvios dentro de cada grupo com repetição
        3. SQ_falta = SQ_residuo - SQ_erro_puro
        4. F = QM_falta / QM_erro_puro
    """
    raise NotImplementedError("Ver issue #4 — ANOVA e seleção de termos.")
