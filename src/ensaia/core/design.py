"""Fatores, planejamento e termos do modelo em notação canônica.
Descreve a geometria do experimento; não faz nenhuma regressão.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from ensaia.core.results import TipoPlanejamento

INTERCEPTO = "Intercepto"


@dataclass(frozen=True)
class Fator:
    """Fator do experimento e os níveis reais que viram −1 e +1."""

    nome: str
    minimo: float
    maximo: float
    unidade: str = ""

    @property
    def centro(self) -> float:
        """Nível real do ponto central (0 codificado)."""
        return (self.minimo + self.maximo) / 2.0

    @property
    def amplitude(self) -> float:
        """Distância real entre os níveis −1 e +1."""
        return self.maximo - self.minimo

    def codificar(self, valor: float) -> float:
        """Converte um nível real para a escala codificada."""
        if self.amplitude == 0:
            raise ValueError(
                f"Fator {self.nome!r} tem amplitude zero "
                f"(mínimo == máximo == {self.minimo}); não é um fator."
            )
        return (valor - self.centro) / (self.amplitude / 2.0)

    def decodificar(self, codificado: float) -> float:
        """Converte um valor codificado de volta para o nível real."""
        return codificado * (self.amplitude / 2.0) + self.centro


@dataclass(frozen=True)
class Planejamento:
    """Tipo do delineamento, fatores, pontos centrais e α axial."""

    tipo: TipoPlanejamento
    fatores: list[Fator]
    n_pontos_centrais: int = 0
    alfa_axial: float | None = None  # só para composto central

    @property
    def k(self) -> int:
        """Número de fatores."""
        return len(self.fatores)

    @property
    def nomes_fatores(self) -> list[str]:
        """Nomes dos fatores, na ordem do planejamento."""
        return [f.nome for f in self.fatores]

    def fator(self, nome: str) -> Fator:
        """Busca um fator pelo nome."""
        for f in self.fatores:
            if f.nome == nome:
                return f
        raise KeyError(f"Fator {nome!r} não existe. Disponíveis: {self.nomes_fatores}")


def termos_do_modelo(
    nomes_fatores: list[str],
    *,
    incluir_quadraticos: bool = True,
    grau_interacao: int = 2,
) -> list[str]:
    """Gera os termos do modelo (lineares, quadráticos, interações)."""
    if grau_interacao < 1:
        raise ValueError("grau_interacao deve ser >= 1")

    termos = [INTERCEPTO]
    termos += list(nomes_fatores)

    if incluir_quadraticos:
        termos += [f"{nome}^2" for nome in nomes_fatores]

    for ordem in range(2, grau_interacao + 1):
        for combo in combinations(nomes_fatores, ordem):
            termos.append(":".join(combo))

    return termos


def nome_legivel(termo: str) -> str:
    """Escreve um termo para leitura humana (a × b, a²)."""
    texto = termo.replace("^2", "²").replace("^3", "³").replace(":", " × ")
    return texto.replace("_", " ")


def interpretar_termo(termo: str) -> list[tuple[str, int]]:
    """Decompõe um termo em pares (fator, potência)."""
    if termo == INTERCEPTO:
        return []

    partes: list[tuple[str, int]] = []
    for pedaco in termo.split(":"):
        nome, separador, potencia = pedaco.rpartition("^")
        if not separador:
            if not pedaco:
                raise ValueError(f"Termo {termo!r} tem um fator vazio.")
            partes.append((pedaco, 1))
            continue
        if not nome or not potencia.isdigit() or int(potencia) < 2:
            raise ValueError(
                f"Termo {termo!r}: a potência de {pedaco!r} deve ser um inteiro "
                f">= 2 (ex.: 'x1^2')."
            )
        partes.append((nome, int(potencia)))
    return partes
