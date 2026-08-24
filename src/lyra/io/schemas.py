"""Validação dos dados experimentais de entrada.

Mensagens de erro aqui são parte do produto, não detalhe técnico. O
usuário-alvo do LYRA não tem formação em programação: "KeyError: 'temp'" não
ajuda ninguém. Toda falha de validação precisa dizer o que está errado, em
qual linha, e o que fazer.
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
        local = ""
        if self.linha is not None:
            local = f" (linha {self.linha}"
            local += f", coluna '{self.coluna}')" if self.coluna else ")"
        elif self.coluna:
            local = f" (coluna '{self.coluna}')"
        return f"[{self.gravidade}]{local} {self.mensagem}"


def validar_dados_experimentais(dados, fatores: list[str], respostas: list[str]):
    """Verifica se a planilha carregada serve para uma análise de DOE.

    TODO(#9): implementar. Verificações mínimas:
        - todas as colunas de fatores e respostas existem
        - valores numéricos (avisar sobre vírgula decimal — planilha
          brasileira exportada em CSV é o caso comum)
        - sem célula vazia nas colunas de fator
        - nº de ensaios >= nº de termos do modelo (senão não há graus de
          liberdade e o ajuste é vacuamente perfeito, R² = 1)
        - avisar quando não há repetição de condição: sem isso, não há teste
          de falta de ajuste
        - avisar sobre fator com um único nível (não é fator)
    """
    raise NotImplementedError("Ver issue #9 — validação de entrada.")
