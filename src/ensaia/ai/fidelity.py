"""Checagem automática de fidelidade: os números do texto vieram da análise?
Decide se um parágrafo da IA entra no relatório e marca o que não bate.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from ensaia.core.facts import fatos_por_secao
from ensaia.core.numeros import Ocorrencia, numero_confere, ocorrencias_numeros
from ensaia.core.results import AnalysisResult

# --- Números rotulados -------------------------------------------------------
# Número logo depois do nome de uma estatística ("o R² de predição foi de 0,79")
# só confere com os valores dela. Sem isso, um R² inventado com 2 casas batia por
# acaso com algum coeficiente, p-valor ou SQ do resultado.

# O que liga o rótulo ao número: "= 0,98", "de 0,98", "foi de cerca de 0,98",
# " (0,98)". Verbo no plural ("foram") não liga: costuma abrir uma lista.
_LIGACAO = (
    r"(?:\s*[=:≈]|\s+\(|\s+(?:foi|é|era|ficou|fica|vale|atingiu|alcançou)"
    r"(?:\s+(?:de|em|igual\s+a))?|\s+(?:de|igual\s+a))?"
    r"(?:\s+(?:aproximadamente|cerca\s+de|apenas))?\s*$"
)
_R2 = r"(?<!\w)(?:[Rr](?:²|\^2)|(?i:coeficiente\s+de\s+determinação))"
_ROTULOS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (chave, re.compile(padrao + _LIGACAO))
    for chave, padrao in (
        ("r2", _R2),
        ("r2_ajustado", _R2 + r"\s*(?i:ajustado|aj\.?|adj\.?)"),
        (
            "r2_predicao",
            _R2 + r"\s*(?i:(?:de\s+)?(?:predição|previsão)|predito|preditivo|pred\.?)",
        ),
        ("r2_maximo", _R2 + r"\s*(?i:máximo)"),
        ("explicada", r"(?<!\w)(?i:explic(?:a|am|ou|aram|ava|ando))(?!\w)"),
        ("p", r"(?<!\w)(?:[pP]|(?i:valor[- ]p|p[- ]valor|valor\s+de\s+p))(?!\w)"),
        (
            "f",
            r"(?<!\w)(?:F(?:\s+(?i:calculado|tabelado|crítico))?|[Rr]azão(?:\s+F)?)"
            r"(?!\w)",
        ),
        ("w", r"(?<!\w)W(?!\w)"),
        ("d", r"(?<!\w)(?:D|[Dd]esejabilidade(?:\s+global)?)(?!\w)"),
    )
)
# Campo do resultado → rótulo com que o texto o cita.
_ROTULO_DO_CAMPO = {
    "r2": "r2",
    "r2_ajustado": "r2_ajustado",
    "r2_predicao": "r2_predicao",
    "r2_maximo": "r2_maximo",
    "valor_p": "p",
    "shapiro_p": "p",
    "valor_f": "f",
    "f_tabelado": "f",
    "razao_f": "f",
    "shapiro_w": "w",
    "desejabilidade_global": "d",
}
# "O modelo explica 95,9% da variação" vale para o R² e para o R² ajustado.
_TAMBEM_EXPLICADA = {"r2", "r2_ajustado"}
# Número seguido de outro ("de 0,985 e 0,959"): o rótulo pode ser do vizinho.
_EM_LISTA = re.compile(r"%?\s*(?:,|\be\b)\s*-?\d")
# Vetores com um valor por ensaio (e o tempo de execução) não são números do
# relatório; com tantos valores, quase todo número de 2 casas batia com algum.
_FORA_DO_TEXTO = frozenset(
    {
        "observados",
        "preditos",
        "residuos",
        "ordem",
        "alavancagem",
        "residuos_studentizados",
        "distancia_cook",
        "tempo_execucao_s",
        "semente",
    }
)


def _rotulo(texto: str, ocorrencia: Ocorrencia) -> str | None:
    """Estatística escrita logo antes do número, se houver."""
    if _EM_LISTA.match(texto, ocorrencia.fim):
        return None
    antes = texto[max(0, ocorrencia.inicio - 80) : ocorrencia.inicio]
    return next((chave for chave, p in _ROTULOS if p.search(antes)), None)


@dataclass(frozen=True)
class Permitidos:
    """Números que um texto fiel pode citar, no geral e por estatística."""

    todos: list[float]
    por_rotulo: dict[str, list[float]]

    def confere(self, texto: str, ocorrencia: Ocorrencia) -> bool:
        """Diz se o número bate; se vier rotulado, só com aquela estatística."""
        rotulo = _rotulo(texto, ocorrencia)
        if rotulo is None:
            return numero_confere(ocorrencia, self.todos)
        return numero_confere(ocorrencia, self.por_rotulo.get(rotulo, []))


def _permitidos(
    fatos: Iterable[str], campos: Iterable[tuple[str, float]] = ()
) -> Permitidos:
    """Junta os números dos fatos (com o rótulo escrito) e os campos do resultado."""
    todos: list[float] = []
    por_rotulo: dict[str, list[float]] = {}

    def anotar(rotulo: str | None, valor: float) -> None:
        todos.append(valor)
        if rotulo is None:
            return
        por_rotulo.setdefault(rotulo, []).append(valor)
        if rotulo in _TAMBEM_EXPLICADA:
            por_rotulo.setdefault("explicada", []).append(valor)

    for fato in fatos:
        for o in ocorrencias_numeros(fato):
            anotar(_rotulo(fato, o), o.valor)
    for campo, valor in campos:
        anotar(_ROTULO_DO_CAMPO.get(campo), valor)
    return Permitidos(todos, por_rotulo)


@dataclass(frozen=True)
class VerificacaoSecao:
    """Veredito da checagem de uma seção."""

    fiel: bool
    numeros_sem_correspondencia: list[float]


def verificar_secao(texto: str, fatos: Sequence[str]) -> VerificacaoSecao:
    """Confere se o texto só cita números presentes nos fatos da seção."""
    permitidos = _permitidos(fatos)
    sem_correspondencia = [
        o.valor for o in ocorrencias_numeros(texto) if not permitidos.confere(texto, o)
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
) -> Permitidos:
    """Números que um texto fiel pode citar: os fatos e o resumo da análise."""
    a = resultado.metadados.alfa if alfa is None else alfa
    fatos = [f for fs in fatos_por_secao(resultado, alfa=a).values() for f in fs]
    campos = [
        (campo, valor)
        for campo, valor in _numeros_em(resultado.model_dump())
        if campo not in _FORA_DO_TEXTO
    ]
    return _permitidos(fatos, [*campos, ("valor_p", a)])


def verificar_texto(
    texto: str,
    resultado: AnalysisResult,
    *,
    alfa: float | None = None,
    valores: Permitidos | None = None,
) -> RelatorioFidelidade:
    """Confere um texto inteiro contra o resultado."""
    a = resultado.metadados.alfa if alfa is None else alfa
    permitidos = (
        valores if valores is not None else valores_do_resultado(resultado, alfa=a)
    )
    numeros = [
        NumeroCitado(o.inicio, o.fim, o.valor, permitidos.confere(texto, o))
        for o in ocorrencias_numeros(texto)
    ]
    return RelatorioFidelidade(numeros, _contradicoes(texto, resultado, a))


def _numeros_em(objeto: object, campo: str = "") -> Iterable[tuple[str, float]]:
    """Números de uma estrutura qualquer, com o campo de cada um (sem booleanos)."""
    if isinstance(objeto, bool):
        return
    if isinstance(objeto, int | float):
        if math.isfinite(objeto):
            yield campo, float(objeto)
        return
    if isinstance(objeto, dict):
        for chave, valor in objeto.items():
            yield from _numeros_em(valor, str(chave))
    elif isinstance(objeto, list | tuple):
        for valor in objeto:
            yield from _numeros_em(valor, campo)


# Afirmações de significância; na dúvida, a frase é ignorada.
_FIM_DE_ORACAO = re.compile(r"\.(?!\d)|[;!?\n]")
_FALA_DE_SIGNIFICANCIA = re.compile(r"significativ|significância", re.IGNORECASE)
_NEGA = re.compile(
    r"\b(?:não|nenhum|nenhuma)\b[^,;]*?significativ|\bsem significância|"
    r"\binsignificante",
    re.IGNORECASE,
)
# Frases sobre termos compostos ("x1:x2", "x1^2") ou com exceções ficam de fora.
_AMBIGUA = re.compile(
    r"quadr|interaç|²|×|\^|\S:\S|\bexceto\b|\bsalvo\b|exceção|\bapenas\b|\bsomente\b|"
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
