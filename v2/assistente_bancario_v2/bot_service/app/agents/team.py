"""Team Banco Ágil V2 — singleton de processo (padrão BANKPER).

O Team contém apenas os 6 agentes pós-autenticação (Saldo, Contas,
Transacoes, Credito, Entrevista, Cambio). A Triagem (autenticação) é
feita por uma state machine determinística em Python (ver
`services/orquestrador.py`).
"""

from __future__ import annotations

from agno.team.team import Team

from assistente_bancario_v2.bot_service.app.agents import (
    agente_cambio,
    agente_contas,
    agente_credito,
    agente_entrevista,
    agente_saldo,
    agente_transacoes,
)
from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_team

_INSTRUCOES_LIDER_V2 = [
    "Membros disponíveis e palavras-chave de roteamento:",
    "- Saldo:       'saldo', 'extrato', 'quanto tenho'",
    "- Contas:      'contas', 'pagar', 'receber', 'vencidas', 'vencimento'",
    "- Transacoes:  'transferir', 'criar transação', 'novo pagamento'",
    "- Credito:     'limite', 'crédito', 'cartão', 'aumento'",
    "- Entrevista:  'score', 'entrevista', 'pontuação', 'melhorar crédito'",
    "- Cambio:      'cotação', 'dólar', 'euro', 'libra', 'câmbio', 'moeda'",
    "Se a mensagem for continuação de um fluxo (entrevista em andamento, ",
    "transação coletando dados), DELEGUE PARA O MESMO AGENTE.",
]

_team: Team | None = None


def obter_team() -> Team | None:
    """Retorna o Team singleton — tenta criar a cada chamada se ainda for None.

    Se `GEMINI_API_KEY` não estiver disponível na primeira chamada, novas chamadas
    vão tentar de novo (útil em testes que injetam a key tarde, hot-reload).
    """
    global _team
    if _team is not None:
        return _team

    membros = []
    for getter in (
        agente_saldo.obter,
        agente_contas.obter,
        agente_transacoes.obter,
        agente_credito.obter,
        agente_entrevista.obter,
        agente_cambio.obter,
    ):
        a = getter()
        if a is not None:
            membros.append(a)

    _team = criar_team(
        nome="BancoAgilV2",
        instrucoes=_INSTRUCOES_LIDER_V2,
        membros=membros,
    )
    return _team


def resetar_team() -> None:
    """Limpa o team singleton (útil em tests)."""
    global _team
    _team = None
