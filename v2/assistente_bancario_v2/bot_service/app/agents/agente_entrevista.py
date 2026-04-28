"""Agente Entrevista — coleta 5 respostas e atualiza score."""

from __future__ import annotations

from agno.agent import Agent

from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_agente
from assistente_bancario_v2.bot_service.app.tools.gateway_tools import atualizar_score_cliente

_agente: Agent | None = None


def obter() -> Agent | None:
    global _agente
    if _agente is None:
        _agente = criar_agente(
            nome="Entrevista",
            descricao="Conduz entrevista financeira e atualiza score do cliente.",
            role="Fazer 5 perguntas em ordem e atualizar score ao final.",
            instrucoes=[
                "Faça UMA pergunta por vez. Aguarde a resposta antes da próxima.",
                "Ordem: 1) renda mensal bruta R$, 2) tipo de emprego (formal/autonomo/desempregado), "
                "3) despesas fixas mensais R$, 4) dependentes (0+), 5) tem dívidas (sim/nao).",
                "Quando tiver as 5, chame atualizar_score_cliente com o id_cliente do prefixo.",
                "Apresente o novo score e ofereça consultar o limite.",
            ],
            tools=[atualizar_score_cliente],
            num_history_runs=20,
        )
    return _agente
