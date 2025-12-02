"""
Testes para a camada de serviços (services/).
Cobre: clientes.py, websocket_manager.py
"""
import pytest
import pandas as pd


class TestLimparCpf:
    """Testes para a função limpar_cpf."""
    
    def test_limpar_cpf_com_pontos_e_traco(self, services_module):
        resultado = services_module.limpar_cpf("123.456.789-01")
        assert resultado == "12345678901"
    
    def test_limpar_cpf_apenas_numeros(self, services_module):
        resultado = services_module.limpar_cpf("12345678901")
        assert resultado == "12345678901"
    
    def test_limpar_cpf_com_espacos(self, services_module):
        resultado = services_module.limpar_cpf(" 123 456 789 01 ")
        assert resultado == "12345678901"


class TestNormalizarData:
    """Testes para a função normalizar_data."""
    
    def test_normalizar_data_formato_brasileiro(self, services_module):
        resultado = services_module.normalizar_data("13/02/1995")
        assert resultado == "1995-02-13"
    
    def test_normalizar_data_formato_iso(self, services_module):
        resultado = services_module.normalizar_data("1995-02-13")
        assert resultado == "1995-02-13"
    
    def test_normalizar_data_com_espacos(self, services_module):
        resultado = services_module.normalizar_data("  13/02/1995  ")
        assert resultado == "1995-02-13"


class TestBuscarClientePorCpf:
    """Testes para buscar_cliente_por_cpf."""
    
    def test_buscar_cliente_existente(self, services_module):
        cliente = services_module.buscar_cliente_por_cpf("12345678901")
        assert cliente is not None
        assert cliente["nome"] == "Cliente Teste"
        assert cliente["cpf"] == "12345678901"
        assert cliente["score_credito"] == 700
    
    def test_buscar_cliente_inexistente(self, services_module):
        cliente = services_module.buscar_cliente_por_cpf("00000000000")
        assert cliente is None
    
    def test_buscar_cliente_com_cpf_formatado(self, services_module):
        cliente = services_module.buscar_cliente_por_cpf("123.456.789-01")
        assert cliente is not None
        assert cliente["nome"] == "Cliente Teste"


class TestAtualizarLimiteCliente:
    """Testes para atualizar_limite_cliente."""
    
    def test_atualizar_limite_sucesso(self, services_module):
        services_module.atualizar_limite_cliente("12345678901", 20000)
        cliente = services_module.buscar_cliente_por_cpf("12345678901")
        assert cliente["limite_credito"] == 20000
    
    def test_atualizar_limite_cliente_inexistente(self, services_module):
        with pytest.raises(ValueError) as exc_info:
            services_module.atualizar_limite_cliente("00000000000", 5000)
        assert "não encontrado" in str(exc_info.value).lower()


class TestAtualizarScoreCliente:
    """Testes para atualizar_score_cliente."""
    
    def test_atualizar_score_sucesso(self, services_module):
        services_module.atualizar_score_cliente("12345678901", 850)
        cliente = services_module.buscar_cliente_por_cpf("12345678901")
        assert cliente["score_credito"] == 850
    
    def test_atualizar_score_cliente_inexistente(self, services_module):
        with pytest.raises(ValueError) as exc_info:
            services_module.atualizar_score_cliente("00000000000", 500)
        assert "não encontrado" in str(exc_info.value).lower()


class TestObterLimitePermitidoPorScore:
    """Testes para obter_limite_permitido_por_score."""
    
    def test_limite_score_baixo(self, services_module):
        # Score 0-499 -> limite 5000 (conforme fixture)
        limite = services_module.obter_limite_permitido_por_score(300)
        assert limite == 5000
    
    def test_limite_score_medio(self, services_module):
        # Score 500-799 -> limite 20000 (conforme fixture)
        limite = services_module.obter_limite_permitido_por_score(600)
        assert limite == 20000
    
    def test_limite_score_alto(self, services_module):
        # Score 800-1000 -> limite 40000 (conforme fixture)
        limite = services_module.obter_limite_permitido_por_score(900)
        assert limite == 40000
    
    def test_limite_score_none(self, services_module):
        limite = services_module.obter_limite_permitido_por_score(None)
        assert limite is None


class TestRegistrarSolicitacaoLimite:
    """Testes para registrar_solicitacao_limite."""
    
    def test_registrar_solicitacao_aprovada(self, csv_environment):
        services = csv_environment["services"]
        clientes_mod = csv_environment["clientes_mod"]
        
        services.registrar_solicitacao_limite(
            cpf="12345678901",
            limite_atual=10000,
            novo_limite=15000,
            status="aprovado"
        )
        
        # Verificar se foi registrado no CSV
        df = pd.read_csv(clientes_mod._SOLICITACOES_CSV)
        assert len(df) == 1
        assert str(df.iloc[0]["cpf_cliente"]) == "12345678901"
        assert df.iloc[0]["status_pedido"] == "aprovado"
    
    def test_registrar_solicitacao_rejeitada(self, csv_environment):
        services = csv_environment["services"]
        clientes_mod = csv_environment["clientes_mod"]
        
        services.registrar_solicitacao_limite(
            cpf="12345678901",
            limite_atual=10000,
            novo_limite=50000,
            status="rejeitado"
        )
        
        df = pd.read_csv(clientes_mod._SOLICITACOES_CSV)
        assert len(df) == 1
        assert df.iloc[0]["status_pedido"] == "rejeitado"


class TestWebsocketManager:
    """Testes para o WebSocket Manager."""
    
    @pytest.mark.asyncio
    async def test_conexao_websocket(self):
        """Testa conexão e desconexão do WebSocket."""
        from services.websocket_manager import ConexaoWebsocket
        from unittest.mock import AsyncMock, MagicMock
        
        manager = ConexaoWebsocket()
        
        # Mock do WebSocket
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        
        # Testar conexão
        await manager.conexao(mock_ws, "test-client")
        assert "test-client" in manager.conexao_ativa
        mock_ws.accept.assert_called_once()
        
        # Testar envio de mensagem
        await manager.enviar_mensagem("test-client", "Hello")
        mock_ws.send_text.assert_called_once_with("Hello")
        
        # Testar desconexão
        manager.desconexao("test-client")
        assert "test-client" not in manager.conexao_ativa
    
    @pytest.mark.asyncio
    async def test_enviar_mensagem_cliente_desconectado(self):
        """Testa que enviar mensagem para cliente desconectado não causa erro."""
        from services.websocket_manager import ConexaoWebsocket
        
        manager = ConexaoWebsocket()
        # Não deve lançar exceção
        await manager.enviar_mensagem("cliente-inexistente", "teste")
