"""Tabela de dados leve, sem pandas.

A especificação do EnsaIA (seção 8.1) pede que o núcleo não dependa de pandas:
os planejamentos de DOE têm dezenas de linhas, e uma estrutura própria de
colunas em numpy resolve com uma fração da memória. `Table` é essa estrutura —
nomes de coluna mais colunas numéricas (`numpy`) ou de texto (`tuple[str, ...]`).

É deliberadamente mínima: só o que a leitura de dados, a montagem da matriz do
modelo e a validação precisam. Nada de índice, de alinhamento automático nem de
operação vetorizada mágica — é um contêiner, não um DataFrame.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

Coluna = NDArray[np.float64] | tuple[str, ...]


@dataclass(frozen=True)
class Table:
    """Colunas nomeadas de dados experimentais, numéricas ou de texto."""

    colunas: tuple[str, ...]
    valores: dict[str, Coluna]

    def __post_init__(self) -> None:
        faltando = [c for c in self.colunas if c not in self.valores]
        if faltando:
            raise ValueError(f"Colunas sem dados: {faltando}.")
        sobrando = [c for c in self.valores if c not in self.colunas]
        if sobrando:
            raise ValueError(f"Dados sem coluna declarada: {sobrando}.")
        tamanhos = {c: len(self.valores[c]) for c in self.colunas}
        if len(set(tamanhos.values())) > 1:
            raise ValueError(f"Colunas com números de linhas diferentes: {tamanhos}.")

    def __len__(self) -> int:
        if not self.colunas:
            return 0
        return len(self.valores[self.colunas[0]])

    def tem(self, nome: str) -> bool:
        return nome in self.valores

    def e_numerica(self, nome: str) -> bool:
        return isinstance(self.valores[nome], np.ndarray)

    def coluna(self, nome: str) -> NDArray[np.float64]:
        """Coluna numérica como array de float.

        Falha alto se a coluna não existe ou não é numérica — é o caminho por
        onde um fator ou resposta com texto no meio é pego cedo, com mensagem
        clara, em vez de virar `NaN` silencioso lá na frente.
        """
        if nome not in self.valores:
            raise KeyError(
                f"Coluna {nome!r} não existe. Colunas: {list(self.colunas)}."
            )
        valor = self.valores[nome]
        if not isinstance(valor, np.ndarray):
            raise ValueError(
                f"Coluna {nome!r} tem valores de texto, não numéricos."
            )
        return valor

    def texto(self, nome: str) -> tuple[str, ...]:
        """Coluna como texto, seja ela numérica ou não (para rótulos, ordem)."""
        valor = self.valores[nome]
        if isinstance(valor, np.ndarray):
            return tuple(_formatar(v) for v in valor)
        return valor

    @classmethod
    def de_colunas(cls, dados: Mapping[str, Sequence[object]]) -> Table:
        """Monta uma `Table` a partir de um dicionário de colunas.

        Cada coluna vira array de float quando TODOS os valores são numéricos
        (aceitando vírgula decimal e célula vazia como `NaN`); caso contrário,
        vira coluna de texto. É assim que o leitor decide o tipo de cada coluna.
        """
        colunas = tuple(dados.keys())
        valores: dict[str, Coluna] = {}
        for nome in colunas:
            bruto = list(dados[nome])
            numerica = _tentar_numerica(bruto)
            valores[nome] = numerica if numerica is not None else tuple(
                str(v).strip() for v in bruto
            )
        return cls(colunas=colunas, valores=valores)


def _tentar_numerica(valores: list[object]) -> NDArray[np.float64] | None:
    """Converte a coluna inteira para float, ou devolve None se algo não for número.

    Célula vazia vira `NaN` (ausência é informação, não erro, nesta camada); a
    verificação de ausência fica para quem monta a matriz do modelo. Vírgula é
    aceita como separador decimal (planilha brasileira).
    """
    saida = np.empty(len(valores), dtype=np.float64)
    for i, valor in enumerate(valores):
        if isinstance(valor, bool):
            return None
        if isinstance(valor, (int, float)):
            saida[i] = float(valor)
            continue
        texto = str(valor).strip()
        if texto == "":
            saida[i] = np.nan
            continue
        try:
            saida[i] = float(texto.replace(",", "."))
        except ValueError:
            return None
    return saida


def _formatar(valor: float) -> str:
    numero = float(valor)
    if np.isnan(numero):
        return ""
    if numero == int(numero):
        return str(int(numero))
    return repr(numero)  # repr do float nativo: "2.5", não "np.float64(2.5)"
