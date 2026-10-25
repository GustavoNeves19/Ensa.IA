"""App FastAPI que junta a interface NiceGUI, o /health e o MCP em /api/mcp.
O comando ensaia-ui sobe este app com Uvicorn.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.util import find_spec

from fastapi import FastAPI
from nicegui import ui

from ensaia.mcp_server.montagem import MCPSobDemanda
from ensaia.ui.home import construir_home
from ensaia.ui.tema import aplicar_tema

# O MCP só é importado na primeira chamada a /api/mcp.
mcp_http = MCPSobDemanda() if find_spec("mcp") is not None else None


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    """Fecha o MCP ao desligar o app, se ele foi ligado."""
    yield
    if mcp_http is not None:
        await mcp_http.encerrar()


app = FastAPI(title="EnsaIA", lifespan=ciclo_de_vida)


@app.get("/health")
def health() -> dict[str, str]:
    """Sonda de saúde: responde que o processo está de pé."""
    return {"status": "ok"}


@ui.page("/")
def pagina_inicial() -> None:
    """Página inicial da interface."""
    aplicar_tema()
    construir_home()


# MCP em /api, montado antes da NiceGUI (que ocupa /).
if mcp_http is not None:
    app.mount("/api", mcp_http)

# Acopla a NiceGUI a este app, sem gravar nada em disco.
ui.run_with(app, title="EnsaIA", favicon="🧪", dark=False, language="pt-BR")


def main() -> None:
    """Sobe o app com Uvicorn (1 worker, sem reload)."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
