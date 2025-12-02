"""
Módulo Tools - Ferramentas para os Agentes do Banco Ágil

Estrutura:
- tools.py: Funções de negócio (validação, consulta de limite, score)
- ferramentas_agentes.py: Ferramentas para agentes (vinculadas à sessão)
"""

from tools.tools import (
    validando_cliente,
    consultando_limite,
    solicitacao_de_limite,
    atualizar_score_cliente,
)

from tools.ferramentas_agentes import (
    # Estado da sessão
    get_session_state,
    limpar_estado_sessao,
    session_states,
    MAX_AUTH_ATTEMPTS,
    # Ferramentas de Triagem
    criar_ferramenta_autenticacao,
    criar_ferramenta_verificar_auth,
    # Ferramentas de Crédito
    criar_ferramenta_consultar_limite,
    criar_ferramenta_solicitar_limite,
    # Ferramentas de Entrevista
    criar_ferramenta_entrevista_credito,
)

__all__ = [
    # tools.py
    "validando_cliente",
    "consultando_limite",
    "solicitacao_de_limite",
    "atualizar_score_cliente",
    # ferramentas_agentes.py - Estado
    "get_session_state",
    "limpar_estado_sessao",
    "session_states",
    "MAX_AUTH_ATTEMPTS",
    # ferramentas_agentes.py - Triagem
    "criar_ferramenta_autenticacao",
    "criar_ferramenta_verificar_auth",
    # ferramentas_agentes.py - Crédito
    "criar_ferramenta_consultar_limite",
    "criar_ferramenta_solicitar_limite",
    # ferramentas_agentes.py - Entrevista
    "criar_ferramenta_entrevista_credito",
]
