"""Orquestração do relatório textual, seção por seção.

Substitui `narrative/chain.py` (LangChain) pelo fluxo da spec §12.3: o código
orquestra, o modelo só reescreve. Para cada seção do relatório:

1. pega os FATOS verificados daquela seção (`core/facts.fatos_por_secao`);
2. no modo M0, o texto é a própria sequência de fatos — determinístico e
   sempre fiel;
3. nos modos M2/M3, monta o prompt da seção, chama o modelo e **checa a
   fidelidade** (`ai/fidelity`): se o texto citar um número que não está nos
   fatos, tenta de novo; persistindo a falha, cai para o texto M0 e registra um
   aviso (spec §12.3.6).

A IA nunca calcula nem escolhe número (ADR 0001): o pior caso é sempre o texto
M0 honesto, nunca um número inventado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from ensaia.ai.client import ClienteModelo, ErroDeIA
from ensaia.ai.fidelity import verificar_secao
from ensaia.ai.prompts import (
    MAX_PALAVRAS_PADRAO,
    PROMPT_VERSION,
    montar_mensagens,
    titulo_secao,
)
from ensaia.core.facts import SECOES, Secao, fatos_por_secao
from ensaia.core.results import AnalysisResult

# M0 não usa IA; M2 é Ollama local; M3 é nuvem com chave do usuário. O modo M1
# (copiar prompt) não gera texto aqui — é a UI que mostra o prompt para o
# usuário colar; por isso não aparece neste fluxo.
Modo = Literal["m0", "m2", "m3"]


@dataclass(frozen=True)
class SecaoTexto:
    """O texto final de uma seção do relatório."""

    secao: Secao
    titulo: str
    texto: str
    # Como o texto foi obtido: True = reescrito pelo modelo; False = texto M0
    # (determinístico), seja por escolha do modo, seja por fallback.
    com_ia: bool


@dataclass(frozen=True)
class RelatorioTextual:
    """Relatório textual completo, pronto para a UI ou o PDF."""

    secoes: list[SecaoTexto]
    modo: Modo
    prompt_version: str
    modelo_usado: str | None = None
    avisos: list[str] = field(default_factory=list)

    def texto_completo(self) -> str:
        return "\n\n".join(f"## {s.titulo}\n\n{s.texto}" for s in self.secoes)


def _texto_m0(fatos: Sequence[str]) -> str:
    """Texto determinístico de uma seção: os próprios fatos, em sequência.

    Os fatos já são frases prontas e verificadas; juntá-las dá um parágrafo
    correto e sempre fiel, sem chamar modelo nenhum.
    """
    return " ".join(fatos)


def gerar_relatorio(
    resultado: AnalysisResult,
    *,
    modo: Modo = "m0",
    cliente: ClienteModelo | None = None,
    max_palavras: int = MAX_PALAVRAS_PADRAO,
    tentativas_fidelidade: int = 2,
) -> RelatorioTextual:
    """Gera o relatório textual a partir do resultado determinístico.

    No modo M0 (ou se nenhum cliente for dado), todas as seções usam o texto
    determinístico. Nos modos M2/M3 é obrigatório passar um `cliente`; cada
    seção é reescrita pelo modelo e só é aceita se passar na checagem de
    fidelidade, caindo para o M0 quando falha.
    """
    if modo != "m0" and cliente is None:
        raise ValueError(f"O modo {modo!r} exige um cliente de modelo.")

    por_secao = fatos_por_secao(resultado)
    secoes: list[SecaoTexto] = []
    avisos: list[str] = []

    for secao in SECOES:
        fatos = por_secao[secao]
        if not fatos:
            continue  # seção sem fatos (ex.: otimização sem ponto ótimo) não entra
        titulo = titulo_secao(secao)

        if modo == "m0" or cliente is None:
            secoes.append(SecaoTexto(secao, titulo, _texto_m0(fatos), com_ia=False))
            continue

        texto = _gerar_secao_com_ia(
            cliente, secao, fatos, max_palavras, tentativas_fidelidade, avisos, titulo
        )
        if texto is not None:
            secoes.append(SecaoTexto(secao, titulo, texto, com_ia=True))
        else:
            secoes.append(SecaoTexto(secao, titulo, _texto_m0(fatos), com_ia=False))

    return RelatorioTextual(
        secoes=secoes,
        modo=modo,
        prompt_version=PROMPT_VERSION,
        modelo_usado=cliente.config.modelo if cliente is not None else None,
        avisos=avisos,
    )


def _gerar_secao_com_ia(
    cliente: ClienteModelo,
    secao: Secao,
    fatos: list[str],
    max_palavras: int,
    tentativas: int,
    avisos: list[str],
    titulo: str,
) -> str | None:
    """Tenta obter um parágrafo fiel do modelo; devolve None se não conseguir.

    Falha de rede (o cliente já tentou de novo internamente) cai direto para o
    M0. Texto infiel é retentado até `tentativas` vezes antes de desistir.
    """
    mensagens = montar_mensagens(secao, fatos, max_palavras=max_palavras)
    for _ in range(max(1, tentativas)):
        try:
            resposta = cliente.completar(mensagens)
        except ErroDeIA as exc:
            avisos.append(
                f"A seção {titulo!r} usou o texto sem IA (M0): "
                f"não foi possível falar com o modelo ({exc})."
            )
            return None
        texto = resposta.texto.strip()
        if verificar_secao(texto, fatos).fiel:
            return texto

    avisos.append(
        f"A seção {titulo!r} usou o texto sem IA (M0): o texto gerado citou "
        f"números fora dos fatos verificados (checagem de fidelidade)."
    )
    return None
