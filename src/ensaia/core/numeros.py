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
from typing import NamedTuple

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


class Ocorrencia(NamedTuple):
    """Um número citado no texto, onde está e com quantas casas foi escrito."""

    inicio: int
    fim: int
    valor: float  # porcentagem já convertida em fração: "5%" → 0,05
    casas: int  # casas decimais escritas: "0,950" → 3, "95%" → 0
    porcentagem: bool


def ocorrencias_numeros(texto: str) -> list[Ocorrencia]:
    """Cada número citado no texto, com a posição e a precisão escrita.

    A posição serve para destacar o trecho na tela (spec §12.5, item 5); as
    casas, para conferir o número pelo arredondamento que o texto usou. Um
    número imediatamente seguido de '%' é lido como fração: "5%" é 0,05 e
    "98,5%" é 0,985. Sem isso, porcentagem e decimal equivalentes contariam como
    números diferentes e a checagem de fidelidade reprovaria uma paráfrase fiel —
    o químico escreve "nível de 5%", o núcleo registra o α como "0,05".
    """
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
    """Todos os números citados no texto, na ordem em que aparecem."""
    return [o.valor for o in ocorrencias_numeros(texto)]


def numero_confere(ocorrencia: Ocorrencia, disponiveis: Iterable[float]) -> bool:
    """True se algum valor disponível, arredondado como o texto escreveu, dá o número.

    É a regra do §12.5 ("considerando o arredondamento usado no texto"): quem
    escreve "0,95" para 0,9504 é fiel; quem escreve "99,2%" quando o resultado é
    1 não é — ao contrário de uma tolerância relativa, que aceitaria os dois.
    """
    # "92,9%" tanto pode ser a fração 0,929 (R² em porcentagem) quanto o próprio
    # valor 92,9 de uma resposta medida em % (remoção, rendimento): vale as duas.
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
