"""Montagem dos prompts da camada de IA, uma seção por vez.

A IA é redatora, não analista (ADR 0001): cada chamada recebe os FATOS já
verificados de UMA seção do relatório e devolve um parágrafo em prosa. O prompt
é prescritivo de propósito — papel, regras numeradas e um exemplo resolvido
(*few-shot*) — porque o alvo são modelos locais pequenos (4B–8B), fracos em
raciocínio, que só precisam reescrever, não decidir (spec §12.3).

Este módulo não chama o modelo (quem faz isso é `ai/client.py`) nem decide o
fluxo (quem faz isso será `ai/report.py`). Ele só constrói o texto do prompt, em
duas formas:

- `montar_mensagens`: a conversa (system + exemplo + fatos) para os modos M2
  (Ollama) e M3 (nuvem), enviada pelo cliente.
- `montar_texto_para_copiar`: o mesmo prompt achatado num texto único para o
  modo M1, em que o usuário cola numa IA de sua escolha.

O texto prescritivo mora em `templates/*.j2` (Jinja2, spec §12.4); os exemplos
few-shot, por serem dados de uma seção, ficam aqui em `_CONFIG`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from ensaia.ai.client import Mensagem
from ensaia.core.facts import SECOES, Secao, fatos_por_secao
from ensaia.core.results import AnalysisResult

# Versionar o prompt é obrigatório: a métrica de fidelidade (§4.3(e)/§12.5) mede
# o desempenho de UM prompt sobre UM modelo. Se o prompt mudar depois da coleta,
# os números da monografia deixam de corresponder ao sistema descrito. Toda
# mudança de texto em templates/ ou nos exemplos abaixo sobe esta etiqueta.
PROMPT_VERSION = "2026.10.2"

# Teto de palavras por seção (spec §12.3, regra 4): parágrafos curtos cabem no
# contexto de modelos pequenos e reduzem a chance de alucinação.
MAX_PALAVRAS_PADRAO = 120

_DIR_TEMPLATES = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class _Exemplo:
    """Um par entrada→saída para ensinar o formato ao modelo (few-shot)."""

    fatos: list[str]
    saida: str


@dataclass(frozen=True)
class _ConfigSecao:
    titulo: str
    exemplo: _Exemplo


# Exemplos resolvidos, um por seção. São fictícios mas plausíveis, e seguem as
# mesmas regras exigidas do modelo (só os números dos fatos, vírgula decimal,
# um parágrafo). É o conteúdo que mais afeta a qualidade do texto gerado —
# revisar com cuidado antes de congelar numa coleta de dados do TCC.
_CONFIG: dict[Secao, _ConfigSecao] = {
    "planejamento": _ConfigSecao(
        titulo="Planejamento experimental",
        exemplo=_Exemplo(
            fatos=[
                "O delineamento é um delineamento Box-Behnken com 3 fatores "
                "('temperatura', 'pH', 'tempo') e 1 resposta ('rendimento').",
                "A matriz experimental tem 17 ensaios.",
            ],
            saida=(
                "O estudo empregou um delineamento Box-Behnken para avaliar três "
                "fatores — temperatura, pH e tempo — sobre o rendimento, "
                "totalizando 17 ensaios experimentais."
            ),
        ),
    ),
    "modelo": _ConfigSecao(
        titulo="Modelo ajustado",
        exemplo=_Exemplo(
            fatos=[
                "O termo 'temperatura' é significativo (p = 0,0005 < 0,05).",
                "O termo 'pH' é significativo (p = 0,0120 < 0,05).",
                "'tempo' não é significativo ao nível de 0,05.",
            ],
            saida=(
                "No modelo ajustado, a temperatura (p = 0,0005) e o pH "
                "(p = 0,0120) tiveram efeito significativo sobre a resposta ao "
                "nível de 5%, enquanto o tempo não apresentou efeito "
                "significativo nesse mesmo nível."
            ),
        ),
    ),
    "anova": _ConfigSecao(
        titulo="Qualidade do ajuste (ANOVA e R²)",
        exemplo=_Exemplo(
            fatos=[
                "O modelo explica 95,0% da variação da resposta 'rendimento' "
                "(R² = 0,950; R² ajustado = 0,930).",
            ],
            saida=(
                "O modelo apresentou bom ajuste aos dados, explicando 95,0% da "
                "variação do rendimento (R² = 0,950; R² ajustado = 0,930)."
            ),
        ),
    ),
    "diagnostico": _ConfigSecao(
        titulo="Diagnóstico do modelo",
        exemplo=_Exemplo(
            fatos=["Não há evidência de falta de ajuste (p = 0,3700 ≥ 0,05)."],
            saida=(
                "O teste de falta de ajuste não foi significativo (p = 0,3700), "
                "o que indica que o modelo descreve adequadamente os dados "
                "experimentais."
            ),
        ),
    ),
    "otimizacao": _ConfigSecao(
        titulo="Otimização",
        exemplo=_Exemplo(
            fatos=[
                "A condição ótima (em níveis codificados) é temperatura = 1,000, "
                "pH = -0,500.",
                "Nessa condição, a resposta prevista é rendimento = 92,5000.",
                "A desejabilidade global no ótimo é D = 0,873.",
            ],
            saida=(
                "A condição ótima foi obtida com a temperatura no nível +1,000 e "
                "o pH em -0,500 (valores codificados), para os quais o modelo "
                "prevê um rendimento de 92,5000. A desejabilidade global de "
                "0,873 indica um ótimo satisfatório."
            ),
        ),
    ),
}


def titulo_secao(secao: Secao) -> str:
    """Título legível de uma seção, para o cabeçalho no relatório."""
    return _CONFIG[secao].titulo


@lru_cache(maxsize=1)
def _ambiente() -> Environment:
    # autoescape desligado: a saída é texto puro (um prompt), não HTML; escapar
    # transformaria aspas e sinais em entidades e sujaria o prompt.
    return Environment(
        loader=FileSystemLoader(_DIR_TEMPLATES),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )


def _prompt_sistema(secao: Secao, max_palavras: int) -> str:
    cfg = _CONFIG[secao]
    modelo = _ambiente().get_template("sistema.j2")
    return modelo.render(titulo=cfg.titulo, max_palavras=max_palavras).strip()


def _bloco_fatos(fatos: Sequence[str]) -> str:
    modelo = _ambiente().get_template("fatos.j2")
    return modelo.render(fatos=list(fatos)).strip()


def montar_mensagens(
    secao: Secao,
    fatos: Sequence[str],
    *,
    max_palavras: int = MAX_PALAVRAS_PADRAO,
) -> list[Mensagem]:
    """Conversa pronta para o cliente (M2/M3): system, exemplo e os fatos reais.

    O exemplo entra como um turno de usuário (os fatos dele) seguido de um turno
    do assistente (a prosa esperada), ensinando o formato antes do pedido real.
    """
    cfg = _CONFIG[secao]
    return [
        Mensagem.sistema(_prompt_sistema(secao, max_palavras)),
        Mensagem.usuario(_bloco_fatos(cfg.exemplo.fatos)),
        Mensagem.assistente(cfg.exemplo.saida),
        Mensagem.usuario(_bloco_fatos(fatos)),
    ]


def montar_texto_para_copiar(
    secao: Secao,
    fatos: Sequence[str],
    *,
    max_palavras: int = MAX_PALAVRAS_PADRAO,
) -> str:
    """O mesmo prompt achatado num texto único, para o modo M1 (copiar e colar).

    Reúne as instruções, o exemplo resolvido e os fatos reais num bloco que o
    usuário cola em qualquer IA. Não depende de rede nem de chave.
    """
    cfg = _CONFIG[secao]
    return (
        f"{_prompt_sistema(secao, max_palavras)}\n\n"
        f"Exemplo.\n"
        f"Entrada:\n{_bloco_fatos(cfg.exemplo.fatos)}\n"
        f"Saída:\n{cfg.exemplo.saida}\n\n"
        f"Agora escreva o parágrafo para estes fatos.\n"
        f"{_bloco_fatos(fatos)}"
    )


def montar_prompt_completo(
    resultado: AnalysisResult,
    *,
    max_palavras: int = MAX_PALAVRAS_PADRAO,
) -> str:
    """O pedido do relatório inteiro num texto só, para o modo M1.

    O usuário copia, cola numa IA de sua escolha (ChatGPT, Gemini, LM Studio…) e
    traz a resposta de volta para a checagem de fidelidade. Modelos grandes de
    conversa não precisam do exemplo resolvido por seção; um pedido único, com
    as seções na ordem, poupa o usuário de colar cinco vezes.
    """
    por_secao = fatos_por_secao(resultado, alfa=resultado.metadados.alfa)
    secoes = [
        {"titulo": titulo_secao(s), "fatos": por_secao[s]}
        for s in SECOES
        if por_secao[s]
    ]
    modelo = _ambiente().get_template("completo.j2")
    return modelo.render(secoes=secoes, max_palavras=max_palavras).strip()


# Garantia de que nenhuma seção ficou sem configuração: se SECOES crescer e
# alguém esquecer de adicionar o prompt, isto falha no import, não em produção.
_faltando = set(SECOES) - set(_CONFIG)
if _faltando:  # pragma: no cover - rede de segurança de desenvolvimento
    raise RuntimeError(f"Seções sem prompt configurado: {sorted(_faltando)}")
