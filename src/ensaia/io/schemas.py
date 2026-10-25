"""Validação dos dados de entrada, com mensagens em português claro.
Cada problema diz o que está errado, em qual linha e o que fazer.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProblemaValidacao:
    """Um problema encontrado nos dados de entrada."""

    gravidade: str  # "erro" | "aviso"
    mensagem: str
    linha: int | None = None
    coluna: str | None = None

    def __str__(self) -> str:
        """Mensagem do problema com linha e coluna."""
        local = ""
        if self.linha is not None:
            local = f" (linha {self.linha}"
            local += f", coluna '{self.coluna}')" if self.coluna else ")"
        elif self.coluna:
            local = f" (coluna '{self.coluna}')"
        return f"[{self.gravidade}]{local} {self.mensagem}"


def validar_dados_experimentais(dados, fatores: list[str], respostas: list[str]):
    """Verifica se a planilha serve para a análise (a implementar)."""
    raise NotImplementedError("Ver issue #9 — validação de entrada.")
