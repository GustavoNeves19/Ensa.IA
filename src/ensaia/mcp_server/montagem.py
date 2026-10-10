"""O MCP por HTTP em `/api/mcp`, carregado só quando alguém o chama.

## Por que "sob demanda"

O servidor web inteiro precisa caber em 512 MB, com no máximo 150 MB parado
(RNF-01). Só importar o SDK do MCP custa uns 23 MB — com a interface já perto
do teto, montá-lo na partida estouraria o orçamento de todo mundo que só usa a
tela. Então `/api` recebe este objeto leve: na primeira requisição ele importa
o servidor, sobe o gerenciador de sessões e daí em diante só repassa.

## Como funciona, do zero

Um app ASGI é só uma função `async (scope, receive, send)` que o Uvicorn chama
a cada requisição. Este objeto é um app ASGI que, na primeira vez, monta o app
de verdade (`server.app_http()`) e passa a delegar para ele.

O gerenciador de sessões do SDK precisa ficar "aberto" (`async with`) enquanto
o servidor vive, numa tarefa só dele: ele roda numa tarefa de fundo que espera
o sinal de parar, dado por `encerrar()` no desligamento do app (o `lifespan` do
FastAPI em `app/main.py`).
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
    """App ASGI que só importa e liga o servidor MCP na primeira requisição."""

    def __init__(self) -> None:
        self._app: AppASGI | None = None
        self._trava = asyncio.Lock()
        self._parar = asyncio.Event()
        self._tarefa: asyncio.Task[None] | None = None

    async def __call__(self, scope: Escopo, receive: Receber, send: Enviar) -> None:
        if scope["type"] == "lifespan":  # app montado não recebe lifespan
            return
        app = await self._garantir()
        await app(scope, receive, send)

    @property
    def carregado(self) -> bool:
        return self._app is not None

    async def encerrar(self) -> None:
        """Fecha o gerenciador de sessões, se ele chegou a ser ligado."""
        if self._tarefa is None:
            return
        self._parar.set()
        await self._tarefa

    async def _garantir(self) -> AppASGI:
        if self._app is not None:
            return self._app
        async with self._trava:
            if self._app is None:
                from ensaia.mcp_server.server import app_http, mcp

                app = app_http()  # cria o gerenciador de sessões
                pronto = asyncio.Event()

                async def manter_aberto() -> None:
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
