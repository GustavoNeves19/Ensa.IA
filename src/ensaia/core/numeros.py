"""Acha números escritos em português num texto e confere se vieram da análise.
Usado pela checagem de fidelidade da IA e pela avaliação manual.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import NamedTuple

# Números em português: 1.234,56 · 1957,37 · 0,85 · 12 · -3,4.
# O primeiro ramo só vale com milhar separado; sem isso, "1957,37" virava 195 e 7,37.
_PADRAO_NUMERO = re.compile(r"-?\d{1,3}(?:\.\d{3})+(?:,\d+)?(?!\d)|-?\d+(?:[.,]\d+)?")


def _para_float(texto: str) -> float | None:
    """Converte um número escrito em português para float."""
    t = texto.strip()
    if "," in t:
        # Tem vírgula: é decimal brasileiro. O ponto é separador de milhar.
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


class Ocorrencia(NamedTuple):
    """Um número citado no texto, com posição e casas decimais."""

    inicio: int
    fim: int
    valor: float  # porcentagem já convertida em fração: "5%" → 0,05
    casas: int  # casas decimais escritas: "0,950" → 3, "95%" → 0
    porcentagem: bool


def ocorrencias_numeros(texto: str) -> list[Ocorrencia]:
    """Cada número citado no texto, com posição e precisão."""
    ocorrencias: list[Ocorrencia] = []
    for m in _PADRAO_NUMERO.finditer(texto):
        bruto = m.group()
        valor = _para_float(bruto)
        if valor is None:
            continue
        separador = "," if "," in bruto else "."
        casas = len(bruto.rpartition(separador)[2]) if separador in bruto else 0
        porcentagem = re.match(r"\s*%", texto[m.end() :]) is not None
        if porcentagem:
            valor /= 100
        ocorrencias.append(Ocorrencia(m.start(), m.end(), valor, casas, porcentagem))
    return ocorrencias


def numeros_no_texto(texto: str) -> list[float]:
    """Todos os números citados no texto, em ordem."""
    return [o.valor for o in ocorrencias_numeros(texto)]


def numero_confere(ocorrencia: Ocorrencia, disponiveis: Iterable[float]) -> bool:
    """Diz se algum valor, arredondado como o texto, dá o número citado."""
    # "92,9%" pode ser 0,929 ou 92,9: vale as duas leituras.
    escalas = (100.0, 1.0) if ocorrencia.porcentagem else (1.0,)
    escrito = ocorrencia.valor * escalas[0]
    folga = 0.5 * 10.0 ** -ocorrencia.casas + 1e-9 * max(1.0, abs(escrito))
    return any(
        abs(d * escala - escrito) <= folga for d in disponiveis for escala in escalas
    )


def numero_rastreavel(
    numero: float,
    disponiveis: Iterable[float],
    *,
    tolerancia_relativa: float = 0.01,
) -> bool:
    """Diz se o número bate com algum valor, a menos de arredondamento."""
    escala = max(abs(numero), 1e-9)
    return any(
        abs(numero - d) <= tolerancia_relativa * max(escala, abs(d))
        for d in disponiveis
    )
