import uuid

from fastapi.testclient import TestClient

from main import app
from agent.constants import STREAM_END_TOKEN

client = TestClient(app)


def test_home_route():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["Status"].startswith("API do Banco Ágil")


def test_websocket_connection():
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
        assert "cpf" in resposta or "autenticado" in resposta
