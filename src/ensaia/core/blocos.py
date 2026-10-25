"""Blocos: a coluna que agrupa ensaios feitos em dias, lotes ou equipamentos.
Entram no modelo como contrastes de soma zero, só para tirar sua diferença do erro.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ensaia.core.design import INTERCEPTO
from ensaia.core.table import Coluna, Table

# Colunas de contraste se chamam "Bloco[B2]", sem ":" nem "^".
_PREFIXO = "Bloco["


@dataclass(frozen=True)
class Blocos:
    """Rótulos de bloco de cada ensaio e as colunas de contraste."""

    coluna: str
    rotulos: tuple[str, ...]  # um por ensaio, na ordem das linhas
    niveis: tuple[str, ...]  # os blocos distintos, na ordem de aparição

    @property
    def n_blocos(self) -> int:
        """Quantos blocos distintos há."""
        return len(self.niveis)

    @property
    def nomes_colunas(self) -> list[str]:
        """Nomes das b − 1 colunas de contraste."""
        return [f"{_PREFIXO}{nivel}]" for nivel in self.niveis[:-1]]

    def colunas(self) -> dict[str, NDArray[np.float64]]:
        """Colunas de contraste de soma zero (+1 no bloco, −1 no último)."""
        rotulos = np.array(self.rotulos, dtype=object)
        ultimo = rotulos == self.niveis[-1]
        return {
            nome: np.where(rotulos == nivel, 1.0, 0.0) - np.where(ultimo, 1.0, 0.0)
            for nome, nivel in zip(self.nomes_colunas, self.niveis[:-1], strict=True)
        }

    def efeitos(self, coeficientes: dict[str, float]) -> dict[str, float]:
        """Efeito de cada bloco em relação à média entre blocos."""
        efeitos = {
            nivel: float(coeficientes[nome])
            for nome, nivel in zip(self.nomes_colunas, self.niveis[:-1], strict=True)
        }
        efeitos[self.niveis[-1]] = -sum(efeitos.values())
        return efeitos


def e_coluna_de_bloco(termo: str) -> bool:
    """Diz se um termo é uma coluna de contraste de bloco."""
    return termo.startswith(_PREFIXO)


def ler_blocos(tabela: Table, coluna: str) -> Blocos:
    """Lê e valida a coluna de bloco (vazios, bloco único, um por ensaio)."""
    if not tabela.tem(coluna):
        raise ValueError(f"A coluna de bloco {coluna!r} não está na planilha.")
    if tabela.e_numerica(coluna):
        valores = tabela.coluna(coluna)
        if np.isnan(valores).any():
            raise ValueError(
                f"A coluna de bloco {coluna!r} tem células vazias: todo ensaio "
                "precisa dizer em que bloco foi feito."
            )
        rotulos = tuple(_rotulo_numerico(float(v)) for v in valores)
    else:
        rotulos = tuple(str(v).strip() for v in tabela.texto(coluna))
        if any(not r for r in rotulos):
            raise ValueError(
                f"A coluna de bloco {coluna!r} tem células vazias: todo ensaio "
                "precisa dizer em que bloco foi feito."
            )
    niveis = tuple(dict.fromkeys(rotulos))
    if len(niveis) < 2:
        raise ValueError(
            f"A coluna de bloco {coluna!r} tem um único bloco: não há diferença "
            "entre blocos a separar. Deixe a coluna em 'Não usar'."
        )
    if len(niveis) >= len(rotulos):
        raise ValueError(
            f"A coluna de bloco {coluna!r} tem um bloco diferente em cada ensaio: "
            "isso parece a numeração dos ensaios, não blocos."
        )
    return Blocos(coluna=coluna, rotulos=rotulos, niveis=niveis)


def com_blocos(matriz: Table, blocos: Blocos | None) -> Table:
    """Insere as colunas de bloco na matriz do modelo, logo após o intercepto."""
    if blocos is None:
        return matriz
    termos = list(matriz.colunas)
    if not termos or termos[0] != INTERCEPTO:
        raise ValueError("A matriz do modelo precisa começar pelo intercepto.")
    colunas_bloco = blocos.colunas()
    nomes = [INTERCEPTO, *colunas_bloco, *termos[1:]]
    valores: dict[str, Coluna] = {t: matriz.coluna(t) for t in termos}
    valores.update(colunas_bloco)
    return Table(colunas=tuple(nomes), valores=valores)


def _rotulo_numerico(valor: float) -> str:
    """Rótulo de texto de um bloco numérico (2 em vez de 2.0)."""
    return str(int(valor)) if valor == int(valor) else f"{valor:g}"
