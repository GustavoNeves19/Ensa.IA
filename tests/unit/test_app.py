"""Testes do processo único (composition root).

Não dirigem a interface no navegador (isso seria teste de ponta a ponta); apenas
confirmam que o app ASGI sobe, que a sonda de saúde responde e que a página
inicial é servida — a garantia mínima de que UI e API coexistem no mesmo app.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from ensaia.app.main import app

cliente = TestClient(app)


def test_health_responde_ok() -> None:
    resposta = cliente.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_pagina_inicial_e_servida() -> None:
    resposta = cliente.get("/")
    assert resposta.status_code == 200
    # O título da marca está no HTML inicial (o conteúdo dinâmico vem depois, via
    # websocket); basta confirmar que a raiz serve a interface, não um 404.
    assert "EnsaIA" in resposta.text
