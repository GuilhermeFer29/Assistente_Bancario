"""Agente Contas — lista contas a pagar/receber/vencidas/pagas."""

from __future__ import annotations

from agno.agent import Agent

from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_agente
from assistente_bancario_v2.bot_service.app.tools.gateway_tools import obter_contas_cliente

_agente: Agent | None = None


def obter() -> Agent | None:
    global _agente
    if _agente is None:
        _agente = criar_agente(
            nome="Contas",
            descricao="Lista contas a pagar, a receber, vencidas ou pagas do cliente.",
            role="Listar contas do cliente com filtros de tipo e período.",
            instrucoes=[
                "Use obter_contas_cliente(id_cliente, tipo, ...).",
                "Tipo: 'a_vencer' (default), 'vencidas', 'pagas'.",
                "id_cliente está no prefixo `[id_cliente=CLI...]` da mensagem.",
                "Apresente em tabela Markdown com descrição, valor, vencimento.",
                "Mostre o total e o valor agregado.",
            ],
            tools=[obter_contas_cliente],
        )
    return _agente
