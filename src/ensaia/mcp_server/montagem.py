"""Monta o MCP por HTTP em /api/mcp, carregado só na primeira chamada.
Evita pagar a memória do SDK do MCP quando ninguém o usa.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

Escopo = MutableMapping[str, Any]
Mensagem = MutableMapping[str, Any]
Receber = Callable[[], Awaitable[Mensagem]]
Enviar = Callable[[Mensagem], Awaitable[None]]
AppASGI = Callable[[Escopo, Receber, Enviar], Awaitable[None]]


class MCPSobDemanda:
    """App ASGI que liga o servidor MCP na primeira requisição."""

    def __init__(self) -> None:
        """Prepara a trava e o sinal de parada."""
        self._app: AppASGI | None = None
        self._trava = asyncio.Lock()
        self._parar = asyncio.Event()
        self._tarefa: asyncio.Task[None] | None = None

    async def __call__(self, scope: Escopo, receive: Receber, send: Enviar) -> None:
        """Atende a requisição, ligando o MCP se preciso."""
        if scope["type"] == "lifespan":  # app montado não recebe lifespan
            return
        app = await self._garantir()
        await app(scope, receive, send)

    @property
    def carregado(self) -> bool:
        """Diz se o MCP já foi ligado."""
        return self._app is not None

    async def encerrar(self) -> None:
        """Fecha o gerenciador de sessões, se foi ligado."""
        if self._tarefa is None:
            return
        self._parar.set()
        await self._tarefa

    async def _garantir(self) -> AppASGI:
        """Importa e liga o servidor MCP uma única vez."""
        if self._app is not None:
            return self._app
        async with self._trava:
            if self._app is None:
                from ensaia.mcp_server.server import app_http, mcp

                app = app_http()  # cria o gerenciador de sessões
                pronto = asyncio.Event()

                async def manter_aberto() -> None:
                    """Mantém o gerenciador de sessões aberto até parar."""
                    async with mcp.session_manager.run():
                        pronto.set()
                        await self._parar.wait()

                self._tarefa = asyncio.create_task(manter_aberto())
                espera = asyncio.create_task(pronto.wait())
                await asyncio.wait(
                    {self._tarefa, espera}, return_when=asyncio.FIRST_COMPLETED
                )
                if not pronto.is_set():  # o gerenciador falhou ao subir
                    espera.cancel()
                    self._tarefa.result()  # relança o erro original
                self._app = app
        return self._app
