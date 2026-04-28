"""Smoke test do healthcheck do banking_gateway."""

from __future__ import annotations

from fastapi.testclient import TestClient

from assistente_bancario_v2.banking_gateway.app.main import app


def test_health_retorna_ok() -> None:
    cliente = TestClient(app)
    resposta = cliente.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "banking_gateway"}
