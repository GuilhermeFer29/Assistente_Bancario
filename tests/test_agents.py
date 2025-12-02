import pytest

from agent import agents


def test_session_state_initialization():
    """Testa a inicialização do estado da sessão."""
    session_id = "teste-sessao"
    state = agents._get_session_state(session_id)
    assert state["autenticado"] is False
    assert state["cpf"] is None
    assert state["bloqueado"] is False


def test_auth_tool_blocks_after_three_erros():
    """Testa que o sistema bloqueia após 3 tentativas falhas."""
    session_id = "sessao-erros-teste"
    # Limpar estado anterior se existir
    if session_id in agents.session_states:
        del agents.session_states[session_id]
    
    autenticar = agents.criar_ferramenta_autenticacao(session_id)

    # Fazer 3 tentativas com dados inválidos
    for i in range(3):
        resposta = autenticar("000", "111")
        print(f"Tentativa {i+1}: {resposta}")

    # Verificar se o estado está bloqueado
    state = agents._get_session_state(session_id)
    assert state["bloqueado"] is True
    
    # A próxima tentativa deve retornar mensagem de bloqueio
    resposta_final = autenticar("000", "111")
    assert "bloqueado" in resposta_final.lower() or "BLOQUEADO" in resposta_final


def test_auth_tool_success():
    """Testa autenticação bem sucedida."""
    session_id = "sessao-sucesso"
    # Limpar estado anterior se existir
    if session_id in agents.session_states:
        del agents.session_states[session_id]
    
    autenticar = agents.criar_ferramenta_autenticacao(session_id)
    
    # Usar dados válidos do CSV
    resposta = autenticar("12345678901", "13/02/1995")
    
    state = agents._get_session_state(session_id)
    assert state["autenticado"] is True
    assert "sucesso" in resposta.lower() or "bem-vindo" in resposta.lower()
