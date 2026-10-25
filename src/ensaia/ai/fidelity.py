"""Checagem automática de fidelidade: os números do texto vieram da análise?
Decide se um parágrafo da IA entra no relatório e marca o que não bate.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from ensaia.core.facts import fatos_por_secao
from ensaia.core.numeros import (
    numero_confere,
    numeros_no_texto,
    ocorrencias_numeros,
)
from ensaia.core.results import AnalysisResult


@dataclass(frozen=True)
class VerificacaoSecao:
    """Veredito da checagem de uma seção."""

    fiel: bool
    numeros_sem_correspondencia: list[float]


def verificar_secao(texto: str, fatos: Sequence[str]) -> VerificacaoSecao:
    """Confere se o texto só cita números presentes nos fatos da seção."""
    permitidos = [n for fato in fatos for n in numeros_no_texto(fato)]
    sem_correspondencia = [
        o.valor
        for o in ocorrencias_numeros(texto)
        if not numero_confere(o, permitidos)
    ]
    return VerificacaoSecao(
        fiel=not sem_correspondencia,
        numeros_sem_correspondencia=sem_correspondencia,
    )


# --- Texto inteiro contra o resultado ----------------------------------------


@dataclass(frozen=True)
class NumeroCitado:
    """Número do texto, sua posição e se bate com o resultado."""

    inicio: int
    fim: int
    valor: float
    rastreavel: bool


@dataclass(frozen=True)
class Contradicao:
    """Afirmação de significância desmentida pelo p-valor."""

    trecho: str
    termo: str
    afirma_significativo: bool
    valor_p: float
    alfa: float

    def descricao(self) -> str:
        """Texto que explica a contradição."""
        p = f"{self.valor_p:.4f}".replace(".", ",")
        a = f"{self.alfa:.2f}".replace(".", ",")
        if self.afirma_significativo:
            return f"O texto diz que '{self.termo}' é significativo, mas p = {p} ≥ {a}."
        return f"O texto diz que '{self.termo}' não é significativo, mas p = {p} < {a}."


@dataclass(frozen=True)
class RelatorioFidelidade:
    """Resultado da checagem de um texto inteiro."""

    numeros: list[NumeroCitado]
    contradicoes: list[Contradicao] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Quantos números o texto cita."""
        return len(self.numeros)

    @property
    def rastreaveis(self) -> int:
        """Quantos números batem com o resultado."""
        return sum(n.rastreavel for n in self.numeros)

    @property
    def nao_rastreaveis(self) -> list[NumeroCitado]:
        """Números que não batem com o resultado."""
        return [n for n in self.numeros if not n.rastreavel]

    @property
    def percentual(self) -> float | None:
        """Fração de números que batem; None sem números."""
        return self.rastreaveis / self.total if self.total else None

    @property
    def fiel(self) -> bool:
        """Diz se tudo bate e não há contradições."""
        return not self.nao_rastreaveis and not self.contradicoes

    def resumo(self) -> str:
        """Resumo da checagem numa frase."""
        if not self.total:
            frase = "O texto não cita números."
        else:
            pct = f"{100 * self.rastreaveis / self.total:.0f}%"
            frase = (
                f"{self.rastreaveis} de {self.total} números conferem com os "
                f"resultados ({pct})."
            )
        n = len(self.contradicoes)
        if n == 1:
            frase += " 1 afirmação de significância contradiz os p-valores."
        elif n > 1:
            frase += f" {n} afirmações de significância contradizem os p-valores."
        return frase


def valores_do_resultado(
    resultado: AnalysisResult, *, alfa: float | None = None
) -> list[float]:
    """Todos os números que um texto fiel pode citar."""
    a = resultado.metadados.alfa if alfa is None else alfa
    valores = list(_numeros_em(resultado.model_dump()))
    for fatos in fatos_por_secao(resultado, alfa=a).values():
        for fato in fatos:
            valores.extend(numeros_no_texto(fato))
    valores.append(a)
    return valores


def verificar_texto(
    texto: str,
    resultado: AnalysisResult,
    *,
    alfa: float | None = None,
    valores: Sequence[float] | None = None,
) -> RelatorioFidelidade:
    """Confere um texto inteiro contra o resultado."""
    a = resultado.metadados.alfa if alfa is None else alfa
    permitidos = (
        valores if valores is not None else valores_do_resultado(resultado, alfa=a)
    )
    numeros = [
        NumeroCitado(o.inicio, o.fim, o.valor, numero_confere(o, permitidos))
        for o in ocorrencias_numeros(texto)
    ]
    return RelatorioFidelidade(numeros, _contradicoes(texto, resultado, a))


def _numeros_em(objeto: object) -> Iterable[float]:
    """Números de uma estrutura qualquer (sem booleanos)."""
    if isinstance(objeto, bool):
        return
    if isinstance(objeto, int | float):
        if math.isfinite(objeto):
            yield float(objeto)
        return
    if isinstance(objeto, dict):
        for valor in objeto.values():
            yield from _numeros_em(valor)
    elif isinstance(objeto, list | tuple):
        for valor in objeto:
            yield from _numeros_em(valor)


# Afirmações de significância; na dúvida, a frase é ignorada.
_FIM_DE_ORACAO = re.compile(r"\.(?!\d)|[;!?\n]")
_FALA_DE_SIGNIFICANCIA = re.compile(r"significativ|significância", re.IGNORECASE)
_NEGA = re.compile(
    r"\b(?:não|nenhum|nenhuma)\b[^,;]*?significativ|\bsem significância|"
    r"\binsignificante",
    re.IGNORECASE,
)
# Frases sobre termos compostos ou com exceções ficam de fora.
_AMBIGUA = re.compile(
    r"quadr|interaç|²|×|\^|\bexceto\b|\bsalvo\b|exceção|\bapenas\b|\bsomente\b|"
    r"\bsó\b|\bmas\b|\bporém\b|\benquanto\b|\bembora\b|\bao passo\b",
    re.IGNORECASE,
)


def _contradicoes(
    texto: str, resultado: AnalysisResult, alfa: float
) -> list[Contradicao]:
    """Afirmações de significância que contradizem os p-valores."""
    achadas: list[Contradicao] = []
    vistas: set[tuple[str, bool]] = set()
    for oracao in _FIM_DE_ORACAO.split(texto):
        if not _FALA_DE_SIGNIFICANCIA.search(oracao) or _AMBIGUA.search(oracao):
            continue
        afirma = not _NEGA.search(oracao)
        citados = [a for a in resultado.ajustes if _menciona(oracao, a.resposta)]
        ajustes = citados or list(resultado.ajustes)
        for fator in resultado.fatores:
            if (fator, afirma) in vistas or not _menciona(oracao, fator):
                continue
            coefs = [c for a in ajustes for c in a.coeficientes if c.termo == fator]
            if afirma and coefs and all(c.valor_p >= alfa for c in coefs):
                p = min(c.valor_p for c in coefs)
            elif not afirma and coefs and all(c.valor_p < alfa for c in coefs):
                p = max(c.valor_p for c in coefs)
            else:
                continue
            vistas.add((fator, afirma))
            achadas.append(Contradicao(oracao.strip(), fator, afirma, p, alfa))
    return achadas


def _menciona(oracao: str, nome: str) -> bool:
    """Diz se o termo aparece como palavra inteira na frase."""
    return any(
        re.search(rf"(?<!\w){re.escape(v)}(?!\w)", oracao, re.IGNORECASE)
        for v in {nome, nome.replace("_", " ")}
    )
