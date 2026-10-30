"""Orquestra o relatório em texto, seção por seção, com ou sem IA.
Com IA, todo o texto vem do modelo; o que não bate com os fatos fica marcado.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from ensaia.ai.client import ClienteModelo
from ensaia.ai.fidelity import RelatorioFidelidade, verificar_secao, verificar_texto
from ensaia.ai.prompts import (
    MAX_PALAVRAS_PADRAO,
    PROMPT_VERSION,
    montar_mensagens,
    titulo_secao,
)
from ensaia.core.facts import SECOES, Secao, fatos_por_secao
from ensaia.core.results import AnalysisResult

# M0 sem IA; M1 texto colado; M2 Ollama local; M3 nuvem.
Modo = Literal["m0", "m1", "m2", "m3"]

NOME_MODO: dict[Modo, str] = {
    "m0": "sem IA (M0)",
    "m1": "IA escolhida pelo usuário, texto colado (M1)",
    "m2": "IA local (M2)",
    "m3": "IA em nuvem (M3)",
}


@dataclass(frozen=True)
class SecaoTexto:
    """Texto final de uma seção do relatório."""

    # None no texto colado (M1), que chega inteiro, sem a divisão por seção.
    secao: Secao | None
    titulo: str
    texto: str
    # True se o modelo reescreveu; False se é o texto sem IA.
    com_ia: bool


@dataclass(frozen=True)
class RelatorioTextual:
    """Relatório em texto completo, com modo e conferência."""

    secoes: list[SecaoTexto]
    modo: Modo
    prompt_version: str
    modelo_usado: str | None = None
    avisos: list[str] = field(default_factory=list)
    # Conferência dos números do texto inteiro.
    fidelidade: RelatorioFidelidade | None = None

    def texto_completo(self) -> str:
        """Relatório com títulos e seções."""
        return "\n\n".join(f"## {s.titulo}\n\n{s.texto}" for s in self.secoes)

    def corpo(self) -> str:
        """Só os textos das seções, sem títulos."""
        return _corpo(self.secoes)

    @property
    def origem(self) -> str:
        """Quem escreveu o texto, em uma linha."""
        nome = NOME_MODO[self.modo]
        return f"{nome}, modelo {self.modelo_usado}" if self.modelo_usado else nome


def _texto_m0(fatos: Sequence[str]) -> str:
    """Texto sem IA de uma seção: os próprios fatos em sequência."""
    return " ".join(fatos)


def gerar_relatorio(
    resultado: AnalysisResult,
    *,
    modo: Modo = "m0",
    cliente: ClienteModelo | None = None,
    max_palavras: int = MAX_PALAVRAS_PADRAO,
    tentativas_fidelidade: int = 2,
    ao_avancar: Callable[[int, int, str], None] | None = None,
) -> RelatorioTextual:
    """Gera o relatório em texto; com IA, falha do modelo sobe como ErroDeIA."""
    if modo == "m1":
        raise ValueError("O modo M1 não chama modelo: use relatorio_colado.")
    if modo != "m0" and cliente is None:
        raise ValueError(f"O modo {modo!r} exige um cliente de modelo.")

    por_secao = fatos_por_secao(resultado)
    secoes: list[SecaoTexto] = []
    avisos: list[str] = []

    # Seção sem fatos (ex.: otimização sem ponto ótimo) não entra.
    com_fatos = [s for s in SECOES if por_secao[s]]
    for n, secao in enumerate(com_fatos, start=1):
        fatos = por_secao[secao]
        titulo = titulo_secao(secao)

        if modo == "m0" or cliente is None:
            secoes.append(SecaoTexto(secao, titulo, _texto_m0(fatos), com_ia=False))
            continue
        if ao_avancar is not None:
            ao_avancar(n, len(com_fatos), titulo)
        texto = _gerar_secao_com_ia(
            cliente, secao, fatos, max_palavras, tentativas_fidelidade, avisos, titulo
        )
        secoes.append(SecaoTexto(secao, titulo, texto, com_ia=True))

    return RelatorioTextual(
        secoes=secoes,
        modo=modo,
        prompt_version=PROMPT_VERSION,
        modelo_usado=cliente.config.modelo if cliente is not None else None,
        avisos=avisos,
        fidelidade=verificar_texto(_corpo(secoes), resultado),
    )


def relatorio_colado(resultado: AnalysisResult, texto: str) -> RelatorioTextual:
    """Relatório a partir do texto colado de uma IA, já conferido."""
    limpo = texto.strip()
    if not limpo:
        raise ValueError("Cole o texto que a IA devolveu.")
    secoes = [SecaoTexto(None, "Texto da sua IA", limpo, com_ia=True)]
    return RelatorioTextual(
        secoes=secoes,
        modo="m1",
        prompt_version=PROMPT_VERSION,
        fidelidade=verificar_texto(limpo, resultado),
    )


def _corpo(secoes: Sequence[SecaoTexto]) -> str:
    """Junta os textos das seções."""
    return "\n\n".join(s.texto for s in secoes)


def _gerar_secao_com_ia(
    cliente: ClienteModelo,
    secao: Secao,
    fatos: list[str],
    max_palavras: int,
    tentativas: int,
    avisos: list[str],
    titulo: str,
) -> str:
    """Pede o parágrafo ao modelo; sem versão fiel, fica a com menos números soltos."""
    mensagens = montar_mensagens(secao, fatos, max_palavras=max_palavras)
    melhor: tuple[int, str] | None = None
    for _ in range(max(1, tentativas)):
        texto = cliente.completar(mensagens).texto.strip()
        soltos = len(verificar_secao(texto, fatos).numeros_sem_correspondencia)
        if not soltos:
            return texto
        if melhor is None or soltos < melhor[0]:
            melhor = (soltos, texto)

    assert melhor is not None
    avisos.append(
        f"A seção {titulo!r} cita números que não estão nos resultados da "
        "análise: eles aparecem em destaque."
    )
    return melhor[1]
