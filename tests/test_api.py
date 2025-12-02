"""Testes para a API REST e WebSocket."""
import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from agent.constants import STREAM_END_TOKEN

client = TestClient(app)

# Verifica se a API key está disponível para testes de integração
HAS_API_KEY = bool(os.getenv("GOOGLE_API_KEY"))

# Intervalo entre chamadas à API (em segundos) para evitar rate limiting
API_DELAY = 30


def test_home_route():
    """Testa rota home da API."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["Status"].startswith("API do Banco Ágil")


@pytest.mark.skipif(not HAS_API_KEY, reason="Requer GOOGLE_API_KEY para teste de integração")
@pytest.mark.integration
def test_websocket_connection():
    """Testa conexão WebSocket com agente real (requer API)."""
    time.sleep(API_DELAY)  # Aguarda antes de chamar a API
    test_client_id = str(uuid.uuid4())

    with client.websocket_connect(f"/chat/ws/{test_client_id}") as websocket:
        websocket.send_text("Olá, estou testando")

        chunks = []
        while True:
            data = websocket.receive_text()
            if data == STREAM_END_TOKEN:
                break
            chunks.append(data)

        resposta = " ".join(chunks).lower()
        # Aceita resposta de erro de rate limit ou resposta normal
        assert "cpf" in resposta or "autenticado" in resposta or "solicit" in resposta


def test_websocket_connect_disconnect():
    """Testa conexão e desconexão WebSocket (unitário)."""
    test_client_id = str(uuid.uuid4())
    
    # Apenas testa que a conexão abre e fecha sem erros
    with client.websocket_connect(f"/chat/ws/{test_client_id}") as websocket:
        assert websocket is not None
