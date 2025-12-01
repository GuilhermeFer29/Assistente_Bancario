import pytest

from agent import agents


def test_session_state_initialization():
    session_id = "teste-sessao"
    state = agents._get_session_state(session_id)
    assert state["authenticated"] is False
    assert state["cpf"] is None


def test_auth_tool_blocks_after_three_erros():
    session_id = "sessao-erros"
    validar = agents.get_auth_tool_for_session(session_id)

    for _ in range(3):
        resposta = validar("000", "111")

    mensagem = resposta.lower()
    assert "bloqueou o acesso" in mensagem or "bloqueado" in mensagem
