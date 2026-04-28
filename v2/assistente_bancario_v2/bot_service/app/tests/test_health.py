"""Smoke test do healthcheck do bot_service."""

from __future__ import annotations

from fastapi.testclient import TestClient

from assistente_bancario_v2.bot_service.app.main import app


def test_health_retorna_ok() -> None:
    cliente = TestClient(app)
    resposta = cliente.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "bot_service"}
