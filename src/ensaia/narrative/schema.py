"""Estrutura da saída da camada de LLM.

O relatório é gerado com estrutura declarada, e não como texto livre, por dois
motivos práticos: a checagem de fidelidade do §4.3(e) precisa segmentar
afirmações, e uma saída estruturada dá onde ancorar cada afirmação à seção que
a originou.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SecaoRelatorio:
    titulo: str
    texto: str


@dataclass(frozen=True)
class NarrativeReport:
    """Relatório técnico em linguagem natural produzido pelo LLM."""

    secoes: list[SecaoRelatorio]
    modelo_usado: str
    prompt_version: str
    avisos: list[str] = field(default_factory=list)

    def texto_completo(self) -> str:
        return "\n\n".join(f"## {s.titulo}\n\n{s.texto}" for s in self.secoes)
