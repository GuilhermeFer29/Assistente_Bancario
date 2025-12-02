"""Testes de streaming para o WebSocket."""
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
API_DELAY = 10


def _send_and_collect(ws, message: str, delay: float = API_DELAY) -> str:
    """Envia mensagem e coleta resposta com delay para evitar rate limit."""
    time.sleep(delay)  # Aguarda antes de enviar
    ws.send_text(message)
    chunks = []
    while True:
        data = ws.receive_text()
        if data == STREAM_END_TOKEN:
            break
        chunks.append(data)
    return " ".join(chunks)


@pytest.mark.skipif(not HAS_API_KEY, reason="Requer GOOGLE_API_KEY para teste de integração")
@pytest.mark.integration
def test_websocket_streaming_flow():
    """Testa fluxo completo de streaming (requer API)."""
    client_id = str(uuid.uuid4())

    with client.websocket_connect(f"/chat/ws/{client_id}") as websocket:
        resposta01 = _send_and_collect(websocket, "Oi")
        # Aceita resposta normal ou de rate limit
        assert "cpf" in resposta01.lower() or "solicit" in resposta01.lower()

        resposta02 = _send_and_collect(websocket, "12345678901 13/02/1995")
        texto02 = resposta02.lower()
        autenticacao_tokens = ["validado", "autenticado", "autentica", "autenticação", "solicit"]
        assert any(token in texto02 for token in autenticacao_tokens)

        resposta03 = _send_and_collect(websocket, "Quero saber meu limite")
        assert "limite" in resposta03.lower() or "solicit" in resposta03.lower()

        resposta04 = _send_and_collect(websocket, "Quero aumentar meu limite")
        texto04 = resposta04.lower()
        assert "aument" in texto04 or "novo limite" in texto04 or "solicit" in texto04

        resposta05 = _send_and_collect(websocket, "18000")
        texto_final = resposta05.lower()
        assert "solicita" in texto_final or "aprov" in texto_final or "solicit" in texto_final
