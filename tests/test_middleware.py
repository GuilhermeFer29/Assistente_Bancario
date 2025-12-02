"""
Testes para o middleware de logging de conexão.
Cobre: middlwares/login_conexao.py
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from middlwares.login_conexao import LoginConexaoMiddleware


@pytest.fixture
def app_with_middleware():
    """Cria uma app FastAPI com o middleware de logging."""
    app = FastAPI()
    app.add_middleware(LoginConexaoMiddleware)
    
    @app.get("/test")
    def test_route():
        return {"message": "ok"}
    
    @app.get("/slow")
    async def slow_route():
        import asyncio
        await asyncio.sleep(0.1)  # Simula operação lenta
        return {"message": "done"}
    
    return app


class TestLoginConexaoMiddleware:
    """Testes para o middleware de logging de conexão."""
    
    def test_middleware_adiciona_header_process_time(self, app_with_middleware):
        client = TestClient(app_with_middleware)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        
        # Tempo de processamento deve ser um número válido
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
    
    def test_middleware_nao_interfere_resposta(self, app_with_middleware):
        client = TestClient(app_with_middleware)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.json() == {"message": "ok"}
    
    def test_middleware_tempo_aumenta_com_operacao_lenta(self, app_with_middleware):
        client = TestClient(app_with_middleware)
        
        response = client.get("/slow")
        
        assert response.status_code == 200
        process_time = float(response.headers["X-Process-Time"])
        # Operação lenta deve ter tempo de processamento maior
        assert process_time >= 0.1
