"""Camada de IA: transforma os fatos verificados em texto, sem fazer contas.
Fala por HTTP com APIs compatíveis com OpenAI (Ollama local ou nuvem).
"""

from __future__ import annotations

from ensaia.ai.client import (
    ClienteModelo,
    ConfiguracaoModelo,
    ErroDeConexao,
    ErroDeIA,
    ErroDeResposta,
    ErroDeTempo,
    Mensagem,
    RespostaInvalida,
    RespostaModelo,
)
from ensaia.ai.fidelity import (
    RelatorioFidelidade,
    VerificacaoSecao,
    verificar_secao,
    verificar_texto,
)
from ensaia.ai.prompts import (
    PROMPT_VERSION,
    montar_mensagens,
    montar_prompt_completo,
    montar_texto_para_copiar,
)
from ensaia.ai.report import (
    RelatorioTextual,
    SecaoTexto,
    gerar_relatorio,
    relatorio_colado,
)

__all__ = [
    "PROMPT_VERSION",
    "ClienteModelo",
    "ConfiguracaoModelo",
    "ErroDeConexao",
    "ErroDeIA",
    "ErroDeResposta",
    "ErroDeTempo",
    "Mensagem",
    "RelatorioFidelidade",
    "RelatorioTextual",
    "RespostaInvalida",
    "RespostaModelo",
    "SecaoTexto",
    "VerificacaoSecao",
    "gerar_relatorio",
    "montar_mensagens",
    "montar_prompt_completo",
    "montar_texto_para_copiar",
    "relatorio_colado",
    "verificar_secao",
    "verificar_texto",
]
