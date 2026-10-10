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
from ensaia.ai.fidelity import RelatorioFidelidade, verificar_secao, verificar_texto
from ensaia.ai.prompts import (
    MAX_PALAVRAS_PADRAO,
    PROMPT_VERSION,
    montar_mensagens,
    titulo_secao,
)
from ensaia.core.facts import SECOES, Secao, fatos_por_secao
from ensaia.core.results import AnalysisResult

# M0 não usa IA; M1 é o texto que o usuário trouxe de uma IA qualquer depois de
# copiar o prompt (não chama modelo aqui: só é conferido, `relatorio_colado`);
# M2 é Ollama local; M3 é nuvem (chave do usuário ou do servidor).
Modo = Literal["m0", "m1", "m2", "m3"]

NOME_MODO: dict[Modo, str] = {
    "m0": "sem IA (M0)",
    "m1": "IA escolhida pelo usuário, texto colado (M1)",
    "m2": "IA local (M2)",
    "m3": "IA em nuvem (M3)",
}


@dataclass(frozen=True)
class SecaoTexto:
    """O texto final de uma seção do relatório."""

    # None no texto colado (M1), que chega inteiro, sem a divisão por seção.
    secao: Secao | None
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
    # Checagem do texto inteiro contra o resultado (spec §12.5), para a tela e o
    # PDF dizerem quantos números conferem.
    fidelidade: RelatorioFidelidade | None = None

    def texto_completo(self) -> str:
        return "\n\n".join(f"## {s.titulo}\n\n{s.texto}" for s in self.secoes)

    def corpo(self) -> str:
        """Só os textos das seções; as posições de `fidelidade` se referem a ele."""
        return _corpo(self.secoes)

    @property
    def origem(self) -> str:
        """Quem escreveu o texto, em uma linha (tela e PDF)."""
        nome = NOME_MODO[self.modo]
        return f"{nome}, modelo {self.modelo_usado}" if self.modelo_usado else nome


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
    if modo == "m1":
        raise ValueError("O modo M1 não chama modelo: use relatorio_colado.")
    if modo != "m0" and cliente is None:
        raise ValueError(f"O modo {modo!r} exige um cliente de modelo.")

    por_secao = fatos_por_secao(resultado)
    secoes: list[SecaoTexto] = []
    avisos: list[str] = []
    # Se o modelo não responde (rede, chave recusada), as demais seções
    # falhariam do mesmo jeito: desiste de vez, com um aviso só.
    sem_conexao = False

    for secao in SECOES:
        fatos = por_secao[secao]
        if not fatos:
            continue  # seção sem fatos (ex.: otimização sem ponto ótimo) não entra
        titulo = titulo_secao(secao)

        if modo == "m0" or cliente is None or sem_conexao:
            secoes.append(SecaoTexto(secao, titulo, _texto_m0(fatos), com_ia=False))
            continue

        try:
            texto = _gerar_secao_com_ia(
                cliente, secao, fatos, max_palavras, tentativas_fidelidade,
                avisos, titulo,
            )
        except ErroDeIA as exc:
            sem_conexao = True
            texto = None
            avisos.append(
                f"O texto ficou sem IA (M0) a partir da seção {titulo!r}: "
                f"não foi possível falar com o modelo ({exc})."
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
        fidelidade=verificar_texto(_corpo(secoes), resultado),
    )


def relatorio_colado(resultado: AnalysisResult, texto: str) -> RelatorioTextual:
    """O texto que o usuário trouxe de uma IA qualquer (M1), já conferido.

    Nada aqui reescreve o texto: ele entra como veio, e a checagem de
    fidelidade diz quantos números batem com o resultado — é o que separa o
    EnsaIA de "jogar a planilha numa IA e confiar".
    """
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
    return "\n\n".join(s.texto for s in secoes)


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

    Texto infiel é retentado até `tentativas` vezes antes de desistir. Falha de
    rede (o cliente já tentou de novo internamente) sobe como `ErroDeIA` para
    quem chamou parar de insistir nas outras seções.
    """
    mensagens = montar_mensagens(secao, fatos, max_palavras=max_palavras)
    for _ in range(max(1, tentativas)):
        texto = cliente.completar(mensagens).texto.strip()
        if verificar_secao(texto, fatos).fiel:
            return texto

    avisos.append(
        f"A seção {titulo!r} usou o texto sem IA (M0): o texto gerado citou "
        f"números fora dos fatos verificados (checagem de fidelidade)."
    )
    return None
