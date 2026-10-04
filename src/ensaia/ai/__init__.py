"""Camada de IA do EnsaIA: redatora, nunca analista.

Transforma o `AnalysisResult` do núcleo (sobretudo o campo de fatos já
verificados) em texto corrido, chamando um modelo de linguagem por HTTP direto.
Não calcula nada: todo número do relatório vem pronto do núcleo (ADR 0001).

A conversa com o modelo é por API compatível com OpenAI (`/v1/chat/completions`),
o que faz um único adaptador atender Ollama local (M2) e nuvem com chave própria
(M3). Ver docs/decisoes/0006-camada-de-ia-httpx-sem-langchain.md.
"""

from __future__ import annotations

from ensaia.ai.client import (
    ClienteModelo,
    ConfiguracaoModelo,
    ErroDeConexao,
    ErroDeIA,
    ErroDeResposta,
    Mensagem,
    RespostaInvalida,
    RespostaModelo,
)

__all__ = [
    "ClienteModelo",
    "ConfiguracaoModelo",
    "ErroDeConexao",
    "ErroDeIA",
    "ErroDeResposta",
    "Mensagem",
    "RespostaInvalida",
    "RespostaModelo",
]
