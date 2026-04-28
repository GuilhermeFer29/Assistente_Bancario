"""Agente Saldo — consulta saldo bancário (lazy global singleton)."""

from __future__ import annotations

from agno.agent import Agent

from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_agente
from assistente_bancario_v2.bot_service.app.tools.gateway_tools import obter_saldo_cliente

_agente: Agent | None = None


def obter() -> Agent | None:
    global _agente
    if _agente is None:
        _agente = criar_agente(
            nome="Saldo",
            descricao="Consulta saldo bancário do cliente.",
            role="Apresentar saldo disponível e bloqueado do cliente.",
            instrucoes=[
                "Use a ferramenta obter_saldo_cliente para buscar o saldo.",
                "O id_cliente vem como `[id_cliente=CLI...]` no início da mensagem — extraia-o e use.",
                "Apresente saldo disponível e saldo bloqueado separadamente.",
                "Formate sempre como R$ X.XXX,XX.",
            ],
            tools=[obter_saldo_cliente],
        )
    return _agente
