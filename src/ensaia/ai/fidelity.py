"""Checagem automática de fidelidade (spec §12.5).

Dois usos, uma mesma régua de números:

- `verificar_secao` é o portão do *fallback*: um parágrafo gerado pelo LLM só
  entra no relatório se todo número que ele cita estiver nos FATOS daquela
  seção. Como os fatos são a única fonte que o modelo recebeu, um número que não
  bate com nenhum deles é candidato a alucinação — e a seção é rejeitada em
  favor do texto M0.
- `verificar_texto` confere um texto inteiro contra o `AnalysisResult`: é o que
  a tela usa para destacar em amarelo os números sem correspondência (inclusive
  no texto que o usuário colou de uma IA qualquer, modo M1) e para apontar
  afirmações de significância que contradizem os p-valores.

Diferente de `validation/fidelity.py`, que estrutura a avaliação MANUAL do
§4.3(e) (classificação humana, planilha): aqui é uma decisão automática, em
tempo de execução. As duas compartilham a extração de números de
`core/numeros.py`.
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
    """Confere se o texto gerado só cita números presentes nos fatos da seção.

    Os números permitidos são os que aparecem nos próprios fatos (que já vieram
    prontos e verificados do núcleo). Qualquer número do texto que não bata com
    nenhum deles, pelo arredondamento que o texto usou, derruba a fidelidade da
    seção.
    """
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
    """Um número do texto, onde ele está e se bate com algum resultado."""

    inicio: int
    fim: int
    valor: float
    rastreavel: bool


@dataclass(frozen=True)
class Contradicao:
    """Uma afirmação de significância que o p-valor do termo desmente."""

    trecho: str
    termo: str
    afirma_significativo: bool
    valor_p: float
    alfa: float

    def descricao(self) -> str:
        p = f"{self.valor_p:.4f}".replace(".", ",")
        a = f"{self.alfa:.2f}".replace(".", ",")
        if self.afirma_significativo:
            return f"O texto diz que '{self.termo}' é significativo, mas p = {p} ≥ {a}."
        return f"O texto diz que '{self.termo}' não é significativo, mas p = {p} < {a}."


@dataclass(frozen=True)
class RelatorioFidelidade:
    """Resultado da checagem de um texto: a métrica (e) do TCC, por texto."""

    numeros: list[NumeroCitado]
    contradicoes: list[Contradicao] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.numeros)

    @property
    def rastreaveis(self) -> int:
        return sum(n.rastreavel for n in self.numeros)

    @property
    def nao_rastreaveis(self) -> list[NumeroCitado]:
        return [n for n in self.numeros if not n.rastreavel]

    @property
    def percentual(self) -> float | None:
        """Fração de números rastreáveis (0–1); None se o texto não tem números."""
        return self.rastreaveis / self.total if self.total else None

    @property
    def fiel(self) -> bool:
        return not self.nao_rastreaveis and not self.contradicoes

    def resumo(self) -> str:
        """Uma frase para a tela e o PDF."""
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
    """Todo número que um texto fiel pode citar: o resultado e os seus fatos.

    O resultado inteiro entra (coeficientes, ANOVA, diagnóstico, ótimo,
    equações…), porque um texto pode citar qualquer valor calculado; os fatos
    entram porque trazem os números já arredondados e as porcentagens que o
    texto costuma repetir.
    """
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
    """Confere um texto inteiro contra o resultado determinístico.

    `valores` permite reaproveitar `valores_do_resultado` ao checar várias
    seções do mesmo resultado sem refazer a lista.
    """
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
    """Números de uma estrutura (dict/list) qualquer; booleanos não contam."""
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


# Afirmações de significância. A leitura é conservadora de propósito: na dúvida,
# a oração é ignorada — um falso alarme na tela custa mais confiança do que uma
# contradição que só a avaliação manual do §4.3(e) vai pegar.
_FIM_DE_ORACAO = re.compile(r"\.(?!\d)|[;!?\n]")
_FALA_DE_SIGNIFICANCIA = re.compile(r"significativ|significância", re.IGNORECASE)
_NEGA = re.compile(
    r"\b(?:não|nenhum|nenhuma)\b[^,;]*?significativ|\bsem significância|"
    r"\binsignificante",
    re.IGNORECASE,
)
# Orações que falam de termos compostos (quadrático, interação) ou que têm
# exceções e contrastes internos ficam de fora: o termo citado pode não ser o
# efeito principal, e a polaridade da frase não é uma só.
_AMBIGUA = re.compile(
    r"quadr|interaç|²|×|\^|\bexceto\b|\bsalvo\b|exceção|\bapenas\b|\bsomente\b|"
    r"\bsó\b|\bmas\b|\bporém\b|\benquanto\b|\bembora\b|\bao passo\b",
    re.IGNORECASE,
)


def _contradicoes(
    texto: str, resultado: AnalysisResult, alfa: float
) -> list[Contradicao]:
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
    """O nome (da coluna ou em leitura humana) aparece como palavra inteira."""
    return any(
        re.search(rf"(?<!\w){re.escape(v)}(?!\w)", oracao, re.IGNORECASE)
        for v in {nome, nome.replace("_", " ")}
    )
