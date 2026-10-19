"""Blocos: a coluna que agrupa ensaios feitos em condições diferentes.

Blocagem é separar os ensaios em grupos (dias, lotes de reagente, equipamentos)
que podem diferir entre si por motivos que não interessam ao estudo. O bloco
não é um fator: não tem nível "mais alto", não se otimiza, e o efeito dele não
vale para um bloco futuro. O que se quer é **tirar** essa diferença do erro,
para que ela não esconda os efeitos dos fatores.

Por isso o bloco entra no modelo como categoria, com b − 1 colunas de contraste
de **soma zero** (codificação de efeitos):

    coluna do bloco j (j = 1 … b−1):  +1 no bloco j, −1 no último bloco, 0 nos demais

Com essa codificação o intercepto é a média entre os blocos, e o efeito de cada
bloco é o quanto ele se afasta dela (o do último é menos a soma dos outros).
Assim, a equação, a superfície, a previsão e a otimização valem para o "bloco
médio" — o certo, já que o bloco de um ensaio futuro é desconhecido.

As colunas de bloco são **termos fixos** do ajuste: ficam sempre no modelo,
não entram nos coeficientes publicados, na ANOVA Tipo II, na equação nem na
redução backward. Na ANOVA da regressão aparecem como a linha "Blocos".
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from ensaia.core.design import INTERCEPTO
from ensaia.core.table import Coluna, Table

# Nome das colunas de contraste: "Bloco[B2]". Sem ":" nem "^", que são da
# notação de termos, para nunca serem lidas como fator ou interação.
_PREFIXO = "Bloco["


@dataclass(frozen=True)
class Blocos:
    """Os rótulos de bloco de cada ensaio e as colunas de contraste."""

    coluna: str
    rotulos: tuple[str, ...]  # um por ensaio, na ordem das linhas
    niveis: tuple[str, ...]  # os blocos distintos, na ordem de aparição

    @property
    def n_blocos(self) -> int:
        return len(self.niveis)

    @property
    def nomes_colunas(self) -> list[str]:
        """Nomes das b − 1 colunas de contraste (o último bloco não tem coluna)."""
        return [f"{_PREFIXO}{nivel}]" for nivel in self.niveis[:-1]]

    def colunas(self) -> dict[str, NDArray[np.float64]]:
        """As colunas de contraste de soma zero, uma por bloco menos o último."""
        rotulos = np.array(self.rotulos, dtype=object)
        ultimo = rotulos == self.niveis[-1]
        return {
            nome: np.where(rotulos == nivel, 1.0, 0.0) - np.where(ultimo, 1.0, 0.0)
            for nome, nivel in zip(self.nomes_colunas, self.niveis[:-1], strict=True)
        }

    def efeitos(self, coeficientes: dict[str, float]) -> dict[str, float]:
        """Efeito de cada bloco (afastamento da média entre blocos).

        `coeficientes` traz os coeficientes das colunas de contraste; o efeito do
        último bloco é menos a soma dos demais (soma zero).
        """
        efeitos = {
            nivel: float(coeficientes[nome])
            for nome, nivel in zip(self.nomes_colunas, self.niveis[:-1], strict=True)
        }
        efeitos[self.niveis[-1]] = -sum(efeitos.values())
        return efeitos


def e_coluna_de_bloco(termo: str) -> bool:
    return termo.startswith(_PREFIXO)


def ler_blocos(tabela: Table, coluna: str) -> Blocos:
    """Lê a coluna de bloco (números ou texto) e valida que ela faz sentido.

    Um bloco só tem sentido se houver ao menos 2 e se cada um reunir mais de um
    ensaio: com um bloco por ensaio, não sobra nada para estimar os fatores.
    """
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
    """A matriz do modelo com as colunas de bloco logo depois do intercepto.

    A posição importa: quando um termo dos fatores é combinação das colunas de
    bloco (confundido com os blocos, como a interação tripla de um fatorial
    dividido em blocos), a busca de termos redundantes, que anda da esquerda para
    a direita, aponta o termo — e não o bloco — como o que sobra.
    """
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
    return str(int(valor)) if valor == int(valor) else f"{valor:g}"
