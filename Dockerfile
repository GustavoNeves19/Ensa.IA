# Imagem de produção do EnsaIA (spec §16.2; RNF-08, RNF-10 e RNF-12).
#
# Dois estágios:
#   1. builder: o uv instala as dependências travadas no uv.lock num ambiente
#      virtual em /app/.venv, junto com o próprio pacote (instalação não
#      editável, ou seja, sem depender do código-fonte depois), e enxuga esse
#      ambiente.
#   2. final: só o Python slim e o .venv pronto. Sem uv, sem código-fonte, sem
#      compiladores: todas as dependências chegam como wheels pré-compiladas.
#
# Extras instalados: ui (NiceGUI/FastAPI/Uvicorn), report (fpdf2 + matplotlib)
# e llm (httpx + Jinja2). O extra dev (testes, lint, statsmodels) fica de fora.

ARG PYTHON_IMAGE=python:3.12-slim

FROM ghcr.io/astral-sh/uv:0.11.27 AS uv

# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS builder

# binutils só no builder: o `strip` enxuga as bibliotecas nativas (ver abaixo).
RUN apt-get update \
    && apt-get install -y --no-install-recommends binutils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /usr/local/bin/uv

# UV_PYTHON aponta o Python da própria imagem; sem isso o uv leria o
# .python-version (3.11) e tentaria baixar outro interpretador.
ENV UV_PYTHON=/usr/local/bin/python3.12 \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=0 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app

# Primeiro só as dependências: esta camada só é refeita quando o uv.lock muda.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --no-editable \
        --extra ui --extra report --extra llm

# Depois o pacote em si (camada que muda a cada commit).
COPY README.md ./
COPY src ./src
RUN uv sync --locked --no-editable \
        --extra ui --extra report --extra llm

# Enxugar o ambiente (RNF-10), sem mudar o que o app executa:
#   - apaga as suítes de teste que as bibliotecas trazem dentro do pacote e os
#     arquivos que só servem para compilar ou checar tipos (.c, .pyx, .pxd, .pyi);
#   - tira os símbolos de depuração das bibliotecas nativas (.so), exceto as que
#     o auditwheel já reescreveu (as que apontam para $ORIGIN: numpy, scipy e
#     Pillow), porque mexer de novo nesses binários pode corrompê-los;
#   - pré-compila (.pyc) só o que o app importa ao subir e ao gerar o PDF: a
#     inicialização fica rápida (RNF-12) sem pagar o .pyc de bibliotecas
#     inteiras que nunca são usadas. O resto compila em memória se for usado.
RUN set -eu; \
    site=/app/.venv/lib/python3.12/site-packages; \
    find "$site" -depth -type d -name tests -exec rm -rf {} +; \
    find "$site" -type f \( -name '*.c' -o -name '*.pyx' -o -name '*.pxd' -o -name '*.pyi' \) -delete; \
    find "$site" -type f \( -name '*.so' -o -name '*.so.*' \) -not -path '*.libs/*' \
        | while read -r so; do \
        grep -qF '$ORIGIN' "$so" || strip --strip-unneeded "$so"; \
    done; \
    MPLBACKEND=Agg /app/.venv/bin/python -c \
        "import ensaia.app.main, ensaia.report, ensaia.ai.report, ensaia.io.readers, ensaia.core.pipeline, matplotlib.pyplot"

# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE}

LABEL org.opencontainers.image.title="EnsaIA" \
      org.opencontainers.image.description="Análise de experimentos químicos (DOE) com interpretação por IA" \
      org.opencontainers.image.source="https://github.com/GustavoNeves19/Ensa.IA" \
      org.opencontainers.image.licenses="MIT"

# MALLOC_ARENA_MAX=2 e MPLBACKEND=Agg: spec §16.2 (orçamento de 512 MB).
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MALLOC_ARENA_MAX=2 \
    MPLBACKEND=Agg \
    PORT=8080

# Usuário sem privilégios. O .venv fica com o root (só leitura para o app);
# a pasta pessoal é gravável para os caches do matplotlib e da NiceGUI.
RUN useradd --create-home --home-dir /home/ensaia --uid 10001 \
        --shell /usr/sbin/nologin ensaia

COPY --from=builder /app/.venv /app/.venv

USER ensaia
WORKDIR /home/ensaia

# Monta o cache de fontes do matplotlib na construção, para o primeiro PDF não
# pagar esse custo durante a requisição.
RUN python -c "import matplotlib.font_manager"

EXPOSE 8080

# Sonda de saúde (RNF-12): a imagem slim não tem curl, então usa o próprio Python.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/health', timeout=4)"]

# Processo único, 1 worker, sem reload (spec §7.2 e §16.2). O `sh -c` existe só
# para expandir ${PORT}; o `exec` deixa o Uvicorn como PID 1, recebendo o
# SIGTERM do Docker para encerrar com elegância.
CMD ["sh", "-c", "exec uvicorn ensaia.app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
