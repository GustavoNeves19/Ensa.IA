"""Cadeia LangChain que traduz um AnalysisResult em relatório técnico.

Terceiro objetivo específico do pré-projeto: "Acoplar uma camada de
interpretação baseada em Modelo de Linguagem de Grande Escala, por meio do
framework LangChain, capaz de traduzir automaticamente os resultados numéricos
do pipeline em relatórios técnicos redigidos em linguagem natural."
"""

from __future__ import annotations

from lyra.core.results import AnalysisResult
from lyra.narrative.schema import NarrativeReport

# Versionar o prompt é obrigatório, não opcional: a métrica de fidelidade do
# §4.3(e) mede o desempenho de UM prompt sobre UM modelo. Se o prompt mudar
# depois da coleta, os números da monografia deixam de corresponder ao sistema
# descrito, e não há como saber sem esta etiqueta.
PROMPT_VERSION = "2026.08.1"


def gerar_relatorio(
    resultado: AnalysisResult,
    *,
    modelo: str | None = None,
    temperatura: float = 0.0,
) -> NarrativeReport:
    """Gera o relatório técnico a partir do resultado determinístico.

    `temperatura=0.0` por padrão. Não é ajuste fino de qualidade: com
    temperatura alta, duas execuções sobre o mesmo AnalysisResult produzem
    relatórios diferentes, e a taxa de fidelidade medida em cada uma vira
    ruído amostral de um experimento não declarado.

    TODO(#7): implementar.
        1. serializar o resultado (resultado.to_json())
        2. montar o prompt a partir de prompts/relatorio_tecnico.md
        3. chamar o modelo via LangChain
        4. registrar modelo, PROMPT_VERSION e avisos no NarrativeReport

    A função recebe `AnalysisResult` e nada mais. Se for preciso um dado que
    não está nele, a correção é adicioná-lo ao contrato do núcleo — não passar
    o DataFrame bruto para cá.
    """
    raise NotImplementedError("Ver issue #7 — camada narrativa.")
