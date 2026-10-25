"""Monta os pedidos (prompts) para a IA, uma seção do relatório por vez.
Papel, regras, um exemplo resolvido e os fatos; os textos ficam em templates/.
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

# Versão do prompt: sobe a cada mudança nos templates ou exemplos.
PROMPT_VERSION = "2026.10.2"

# Teto de palavras por seção.
MAX_PALAVRAS_PADRAO = 120

_DIR_TEMPLATES = Path(__file__).parent / "templates"


@dataclass(frozen=True)
class _Exemplo:
    """Par entrada→saída que ensina o formato ao modelo."""

    fatos: list[str]
    saida: str


@dataclass(frozen=True)
class _ConfigSecao:
    """Título e exemplo de uma seção do relatório."""

    titulo: str
    exemplo: _Exemplo


# Exemplos resolvidos, um por seção (fictícios, mas plausíveis).
_CONFIG: dict[Secao, _ConfigSecao] = {
    "planejamento": _ConfigSecao(
        titulo="Planejamento experimental",
        exemplo=_Exemplo(
            fatos=[
                "O delineamento é um delineamento composto central rotacional "
                "(DCCR) com 3 fatores ('temperatura', 'pH', 'tempo') e 1 "
                "resposta ('rendimento').",
                "A matriz experimental tem 20 ensaios.",
            ],
            saida=(
                "O estudo empregou um delineamento composto central rotacional "
                "(DCCR) para avaliar três fatores — temperatura, pH e tempo — "
                "sobre o rendimento, totalizando 20 ensaios experimentais."
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
    """Título legível de uma seção."""
    return _CONFIG[secao].titulo


@lru_cache(maxsize=1)
def _ambiente() -> Environment:
    # Sem autoescape: a saída é texto puro, não HTML.
    """Ambiente Jinja2 que carrega os templates."""
    return Environment(
        loader=FileSystemLoader(_DIR_TEMPLATES),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )


def _prompt_sistema(secao: Secao, max_palavras: int) -> str:
    """Instrução de sistema de uma seção."""
    cfg = _CONFIG[secao]
    modelo = _ambiente().get_template("sistema.j2")
    return modelo.render(titulo=cfg.titulo, max_palavras=max_palavras).strip()


def _bloco_fatos(fatos: Sequence[str]) -> str:
    """Lista de fatos formatada para o pedido."""
    modelo = _ambiente().get_template("fatos.j2")
    return modelo.render(fatos=list(fatos)).strip()


def montar_mensagens(
    secao: Secao,
    fatos: Sequence[str],
    *,
    max_palavras: int = MAX_PALAVRAS_PADRAO,
) -> list[Mensagem]:
    """Conversa pronta para a IA local ou de nuvem."""
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
    """O pedido de uma seção num texto só, para copiar."""
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
    """O pedido do relatório inteiro num texto só, para copiar."""
    por_secao = fatos_por_secao(resultado, alfa=resultado.metadados.alfa)
    secoes = [
        {"titulo": titulo_secao(s), "fatos": por_secao[s]}
        for s in SECOES
        if por_secao[s]
    ]
    modelo = _ambiente().get_template("completo.j2")
    return modelo.render(secoes=secoes, max_palavras=max_palavras).strip()


# Toda seção precisa de configuração (falha no import se faltar).
_faltando = set(SECOES) - set(_CONFIG)
if _faltando:  # pragma: no cover - rede de segurança de desenvolvimento
    raise RuntimeError(f"Seções sem prompt configurado: {sorted(_faltando)}")
