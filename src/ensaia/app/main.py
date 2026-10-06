"""Processo único ASGI: a interface web, a sonda de saúde e (depois) o MCP.

## O que é isto, do zero

Um programa web precisa de duas peças: um *framework* que decide o que responder
a cada endereço (as "rotas") e um *servidor* que fica escutando a rede e entrega
essas respostas. Aqui o framework é o **FastAPI** e o servidor é o **Uvicorn**.

A spec (seção 7.2) exige que a interface web, o servidor MCP e a sonda de saúde
rodem **no mesmo processo** (um único Uvicorn, um *worker*), porque três
processos separados não caberiam no orçamento de 512 MB de memória (RNF-01).

Então este arquivo é o ponto onde tudo se junta:

- `app` é o objeto FastAPI. É ele que o Uvicorn executa.
- `GET /health` é uma rota simples que responde "estou de pé" — usada por quem
  hospeda o sistema para saber se já pode mandar tráfego (RNF-12).
- `@ui.page("/")` registra a página inicial da interface na raiz.
- `ui.run_with(app, ...)` **acopla** a NiceGUI a este mesmo `app` em vez de subir
  um servidor próprio — é isso que mantém tudo num processo só.

O servidor MCP entra na fase F9 (a última), montado em `/api`, no ponto marcado
abaixo. Não se monta o MCP em `/` para não encobrir as páginas da interface.

## Como subir

    ensaia-ui                       # script instalado (ver pyproject)
    # ou, equivalentemente:
    uvicorn ensaia.app.main:app     # 1 worker, sem reload em produção
"""

from __future__ import annotations

from fastapi import FastAPI
from nicegui import ui

from ensaia.ui.home import construir_home
from ensaia.ui.tema import aplicar_tema

app = FastAPI(title="EnsaIA")


@app.get("/health")
def health() -> dict[str, str]:
    """Sonda de saúde: confirma que o processo subiu e responde (RNF-12)."""
    return {"status": "ok"}


@ui.page("/")
def pagina_inicial() -> None:
    """Página inicial da interface web."""
    aplicar_tema()
    construir_home()


# TODO(fase F9): montar o servidor MCP em "/api" aqui (ensaia.mcp_server),
# iniciando o gerenciador de sessões no lifespan do app. Ver spec, seção 7.2.

# Acopla a NiceGUI a este app (sem storage_secret: nada é persistido em disco —
# princípio P1; usamos apenas o estado em memória da sessão).
ui.run_with(app, title="EnsaIA", favicon="🧪", dark=False)


def main() -> None:
    """Sobe o processo único com Uvicorn (1 worker, sem reload) — RNF-01/RNF-12."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8080)
