"""Extração e rastreio de números escritos em português dentro de um texto.

Utilidade pura e compartilhada. Duas checagens diferentes precisam da mesma
operação — achar os números citados num texto e dizer se cada um corresponde a
um valor que o pipeline realmente produziu:

- a checagem automática de fidelidade em tempo de execução (`ai/fidelity.py`),
  que decide se um parágrafo do LLM pode entrar no relatório;
- a avaliação manual do §4.3(e) (`validation/fidelity.py`), que estrutura a
  classificação humana das afirmações.

A lógica é só regex e aritmética — sem rede, sem LLM, sem cálculo estatístico —
e fica no núcleo para ter uma só fonte de verdade. O núcleo já formata números
no padrão brasileiro (vírgula decimal); aqui ele os lê de volta.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

# Números em português: 1234,56 · 1.234,56 · 0,85 · 12 · -3,4 · 1.2
# (o separador de milhar é ponto; o decimal é vírgula).
_PADRAO_NUMERO = re.compile(r"-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:[.,]\d+)?")


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


def numeros_no_texto(texto: str) -> list[float]:
    """Todos os números citados no texto, na ordem em que aparecem.

    Um número imediatamente seguido de '%' é lido como fração: "5%" é 0,05 e
    "98,5%" é 0,985. Sem isso, porcentagem e decimal equivalentes contariam como
    números diferentes e a checagem de fidelidade reprovaria uma paráfrase fiel —
    o químico escreve "nível de 5%", o núcleo registra o α como "0,05".
    """
    numeros: list[float] = []
    for m in _PADRAO_NUMERO.finditer(texto):
        valor = _para_float(m.group())
        if valor is None:
            continue
        if re.match(r"\s*%", texto[m.end() :]):
            valor /= 100
        numeros.append(valor)
    return numeros


def numero_rastreavel(
    numero: float,
    disponiveis: Iterable[float],
    *,
    tolerancia_relativa: float = 0.01,
) -> bool:
    """True se `numero` corresponde a algum valor disponível, a menos de arredondamento.

    A tolerância é relativa à maior das magnitudes comparadas, para funcionar
    tanto com p-valores minúsculos quanto com somas de quadrados grandes. Um
    texto que escreve "aproximadamente 95%" ainda bate com 0,95 do resultado.
    """
    escala = max(abs(numero), 1e-9)
    return any(
        abs(numero - d) <= tolerancia_relativa * max(escala, abs(d))
        for d in disponiveis
    )
