"""Provedores de modelo de linguagem que a tela oferece (spec §12.2).

Todos falam a API compatível com OpenAI, então um provedor é só uma URL base,
se precisa de chave e como escolher um bom modelo na lista que ele devolve. A
lista vem do próprio provedor (`GET /models`): os nomes mudam a cada geração de
modelos, e pedir que um químico adivinhe "gemini-x.y-flash" seria cruel.

A chave do usuário (M3, BYOK) nunca passa por aqui: quem a guarda é a sessão da
tela, só na memória. Este módulo só lê a chave do SERVIDOR, quando quem hospeda
o EnsaIA decidiu oferecer uma IA pronta (variáveis de ambiente ou `.env`).
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ensaia.ai.client import ConfiguracaoModelo


@dataclass(frozen=True)
class Provedor:
    """Um serviço compatível com OpenAI e o jeito de escolher modelo nele."""

    id: str
    nome: str
    url_base: str
    # Onde o usuário cria a chave (None: provedor local, sem chave).
    onde_criar_chave: str | None
    # Trechos do nome, em ordem de preferência, para sugerir um modelo.
    preferidos: tuple[str, ...]
    # Trechos que marcam modelos que não escrevem texto (voz, imagem, embeddings).
    evitar: tuple[str, ...]


_NAO_TEXTO = (
    "embed",
    "tts",
    "audio",
    "transcri",
    "whisper",
    "image",
    "imagen",
    "vision",
    "realtime",
    "live",
    "moderation",
    "guard",
    "dall-e",
    "veo",
    "aqa",
    "search",
)

PROVEDORES: dict[str, Provedor] = {
    "gemini": Provedor(
        "gemini",
        "Google Gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "https://aistudio.google.com/apikey",
        ("flash", "pro"),
        (*_NAO_TEXTO, "gemma", "learnlm", "robotics", "computer"),
    ),
    "groq": Provedor(
        "groq",
        "Groq",
        "https://api.groq.com/openai/v1",
        "https://console.groq.com/keys",
        ("llama-3.3-70b", "gpt-oss", "llama", "qwen"),
        (*_NAO_TEXTO, "playai", "distil", "compound"),
    ),
    "openai": Provedor(
        "openai",
        "OpenAI",
        "https://api.openai.com/v1",
        "https://platform.openai.com/api-keys",
        ("gpt-4o-mini", "mini", "gpt-4o"),
        (*_NAO_TEXTO, "davinci", "babbage", "codex", "computer", "o1-pro"),
    ),
}

OLLAMA = Provedor(
    "ollama",
    "Ollama",
    "http://localhost:11434/v1",
    None,
    ("qwen3", "llama3", "gemma3", "qwen"),
    ("embed",),
)


def modelos_de_texto(provedor: Provedor, nomes: Iterable[str]) -> list[str]:
    """Só os modelos que escrevem texto, em ordem alfabética."""
    return sorted(n for n in nomes if not any(t in n.lower() for t in provedor.evitar))


def modelo_sugerido(provedor: Provedor, nomes: Iterable[str]) -> str | None:
    """O modelo que a tela já deixa escolhido; o usuário pode trocar.

    Segue a ordem de `preferidos`: o nome exato, se existir; senão a versão mais
    nova que contém o trecho, preferindo as estáveis às de prévia e o nome mais
    curto (o modelo "base", não a variante).
    """
    candidatos = modelos_de_texto(provedor, nomes)
    for trecho in provedor.preferidos:
        if trecho in candidatos:
            return trecho
        achados = [n for n in candidatos if trecho in n.lower()]
        estaveis = [n for n in achados if not _e_previa(n)]
        if estaveis or achados:
            return max(estaveis or achados, key=_ordem_versao)
    return candidatos[0] if candidatos else None


def _e_previa(nome: str) -> bool:
    return any(t in nome.lower() for t in ("preview", "exp", "beta"))


def _ordem_versao(nome: str) -> tuple[tuple[int, ...], int]:
    numeros = tuple(int(n) for n in re.findall(r"\d+", nome))
    return numeros, -len(nome)


# --- IA oferecida pelo servidor --------------------------------------------


def config_do_servidor(arquivo_env: Path | None = None) -> ConfiguracaoModelo | None:
    """A IA que quem hospeda o EnsaIA oferece pronta, ou None se não houver.

    Lê `ENSAIA_IA_CHAVE` (ou `OPENAI_API_KEY`), `ENSAIA_IA_URL` (padrão: OpenAI)
    e `ENSAIA_IA_MODELO` (ou `ENSAIA_MODELO_OPENAI`; padrão: gpt-4o-mini). O
    `.env` da raiz do projeto, quando existe, preenche o que o ambiente não
    trouxe — nunca sobrescreve.
    """
    _carregar_env(arquivo_env or Path(__file__).resolve().parents[3] / ".env")
    chave = os.environ.get("ENSAIA_IA_CHAVE") or os.environ.get("OPENAI_API_KEY")
    if not chave:
        return None
    modelo = (
        os.environ.get("ENSAIA_IA_MODELO")
        or os.environ.get("ENSAIA_MODELO_OPENAI")
        or "gpt-4o-mini"
    )
    return ConfiguracaoModelo(
        url_base=os.environ.get("ENSAIA_IA_URL") or PROVEDORES["openai"].url_base,
        modelo=modelo,
        chave_api=chave,
    )


def url_ollama() -> str | None:
    """URL do Ollama configurada pelo servidor (`ENSAIA_OLLAMA_URL`), se houver."""
    return os.environ.get("ENSAIA_OLLAMA_URL") or None


def _carregar_env(caminho: Path) -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))
