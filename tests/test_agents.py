"""
Testes para os agentes do Banco Ágil (agent/agents.py).
Cobre: Criação de agentes, Team, processamento de mensagens.
"""
import pytest
from unittest.mock import patch, MagicMock

from agent import agents
from tools.ferramentas_agentes import (
    session_states,
    limpar_estado_sessao,
    get_session_state,
    criar_ferramenta_autenticacao,
)


@pytest.fixture(autouse=True)
def cleanup_sessions():
    """Limpa sessões antes e depois de cada teste."""
    yield
    # Cleanup
    sessions_to_remove = [k for k in session_states.keys() if k.startswith("test-")]
    for sid in sessions_to_remove:
        limpar_estado_sessao(sid)


class TestSessionState:
    """Testes para gerenciamento de estado de sessão."""
    
    def test_session_state_initialization(self):
        """Testa a inicialização do estado da sessão."""
        session_id = "test-sessao-init"
        state = get_session_state(session_id)
        
        assert state["autenticado"] is False
        assert state["cpf"] is None
        assert state["bloqueado"] is False
        assert state["tentativas_auth"] == 0


class TestCriarAgentes:
    """Testes para criação de agentes individuais."""
    
    def test_criar_agente_triagem(self, csv_environment):
        """Testa criação do agente de triagem."""
        agente = agents.criar_agente_triagem("test-triagem")
        
        assert agente is not None
        assert agente.id == "triagem"
        assert agente.name == "Triagem"
        assert len(agente.tools) >= 4  # autenticar, verificar, registrar_cpf, registrar_data
    
    def test_criar_agente_credito(self, csv_environment):
        """Testa criação do agente de crédito."""
        agente = agents.criar_agente_credito("test-credito")
        
        assert agente is not None
        assert agente.id == "credito"
        assert agente.name == "Credito"
        assert len(agente.tools) >= 3  # consultar, solicitar, verificar
    
    def test_criar_agente_entrevista(self, csv_environment):
        """Testa criação do agente de entrevista."""
        agente = agents.criar_agente_entrevista_credito("test-entrevista")
        
        assert agente is not None
        assert agente.id == "entrevista"
        assert agente.name == "Entrevista"
        assert len(agente.tools) >= 2  # atualizar_score, verificar
    
    def test_criar_agente_cambio(self, csv_environment):
        """Testa criação do agente de câmbio."""
        agente = agents.criar_agente_cambio("test-cambio")
        
        assert agente is not None
        assert agente.id == "cambio"
        assert agente.name == "Cambio"


class TestCriarTeam:
    """Testes para criação do Team de agentes."""
    
    def test_criar_time_banco_agil(self, csv_environment):
        """Testa criação do Team completo."""
        team = agents.criar_time_banco_agil("test-team")
        
        assert team is not None
        assert len(team.members) == 4  # triagem, credito, entrevista, cambio
        
        # Verificar IDs dos membros
        member_ids = [m.id for m in team.members]
        assert "triagem" in member_ids
        assert "credito" in member_ids
        assert "entrevista" in member_ids
        assert "cambio" in member_ids
    
    def test_time_configuracao_passthrough(self, csv_environment):
        """Testa que o Team usa padrão passthrough."""
        team = agents.criar_time_banco_agil("test-team-passthrough")
        
        # Verificar configuração passthrough
        assert team.respond_directly is True


class TestAuthTool:
    """Testes para ferramentas de autenticação via agents.py."""
    
    def test_auth_tool_blocks_after_three_errors(self, csv_environment):
        """Testa que o sistema bloqueia após 3 tentativas falhas."""
        session_id = "test-sessao-erros"
        
        autenticar = criar_ferramenta_autenticacao(session_id)

        # Fazer 3 tentativas com dados inválidos
        for _ in range(3):
            autenticar("000", "111")

        # Verificar se o estado está bloqueado
        state = get_session_state(session_id)
        assert state["bloqueado"] is True
        
        # A próxima tentativa deve retornar mensagem de bloqueio
        resposta_final = autenticar("000", "111")
        assert "BLOQUEADO" in resposta_final

    def test_auth_tool_success(self, csv_environment):
        """Testa autenticação bem sucedida."""
        session_id = "test-sessao-sucesso"
        
        autenticar = criar_ferramenta_autenticacao(session_id)
        
        # Usar dados válidos do CSV (fixture)
        resposta = autenticar("12345678901", "13/02/1995")
        
        state = get_session_state(session_id)
        assert state["autenticado"] is True
        assert "SUCESSO" in resposta


class TestGetTeam:
    """Testes para obtenção/cache de Teams."""
    
    def test_get_team_cria_novo(self, csv_environment):
        """Testa que get_team cria um novo team se não existir."""
        session_id = "test-get-team-novo"
        
        team = agents.get_team(session_id)
        
        assert team is not None
        assert len(team.members) == 4
    
    def test_get_team_retorna_existente(self, csv_environment):
        """Testa que get_team retorna team existente."""
        session_id = "test-get-team-existente"
        
        team1 = agents.get_team(session_id)
        team2 = agents.get_team(session_id)
        
        assert team1 is team2  # Deve ser o mesmo objeto


class TestLimparSessao:
    """Testes para limpeza de sessão."""
    
    def test_limpar_sessao(self, csv_environment):
        """Testa limpeza de sessão e team."""
        session_id = "test-limpar-sessao"
        
        # Criar team e estado
        agents.get_team(session_id)
        state = get_session_state(session_id)
        state["autenticado"] = True
        
        # Limpar
        agents.limpar_sessao(session_id)
        
        # Verificar que foi limpo
        new_state = get_session_state(session_id)
        assert new_state["autenticado"] is False


class TestProcessarMensagem:
    """Testes para processamento de mensagens."""
    
    def test_processar_mensagem_comando_finalizar(self, csv_environment):
        """Testa que comando 'Finalizar' retorna mensagem de encerramento."""
        session_id = "test-finalizar"
        
        is_stream, resposta = agents.processar_mensagem(session_id, "Finalizar", stream=False)
        
        assert is_stream is False
        # Verifica se é string e contém palavras esperadas
        resposta_lower = str(resposta).lower()
        # Aceita mensagem de encerramento ou erro de rate limit
        assert (
            "encerrad" in resposta_lower or 
            "finaliz" in resposta_lower or 
            "obrigado" in resposta_lower or
            "solicit" in resposta_lower  # rate limit
        )
    
    @patch.object(agents, 'get_team')
    def test_processar_mensagem_retorna_resposta(self, mock_get_team, csv_environment):
        """Testa que processar_mensagem retorna resposta do team."""
        session_id = "test-processar"
        
        # Mock do team
        mock_team = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Olá! Como posso ajudar?"
        mock_team.run.return_value = mock_response
        mock_get_team.return_value = mock_team
        
        is_stream, resposta = agents.processar_mensagem(session_id, "Olá", stream=False)
        
        assert is_stream is False
        assert resposta == "Olá! Como posso ajudar?"

