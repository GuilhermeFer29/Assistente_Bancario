"""Agente Câmbio — cotações via Tavily."""

from __future__ import annotations

from agno.agent import Agent
from agno.tools.tavily import TavilyTools

from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_agente
from assistente_bancario_v2.bot_service.app.core.config import configuracao_bot

_agente: Agent | None = None


def obter() -> Agent | None:
    global _agente
    if _agente is None:
        tools: list = []
        if configuracao_bot.tavily_api_key:
            tools.append(TavilyTools(api_key=configuracao_bot.tavily_api_key))
        _agente = criar_agente(
            nome="Cambio",
            descricao="Cotações de moedas estrangeiras (dólar, euro, libra, peso).",
            role="Apresentar cotações atualizadas em tabela Markdown.",
            instrucoes=[
                "Use TavilyTools para buscar cotações na web.",
                "Apresente em tabela: Compra | Venda.",
                "Cite a fonte e diga que cotações são referenciais.",
            ],
            tools=tools,
        )
    return _agente
