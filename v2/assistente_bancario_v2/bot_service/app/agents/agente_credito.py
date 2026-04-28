"""Agente Crédito — consulta limite e solicita aumento (Step-Up)."""

from __future__ import annotations

from agno.agent import Agent

from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_agente
from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
    consultar_limite_credito,
    solicitar_aumento_de_limite,
)

_agente: Agent | None = None


def obter() -> Agent | None:
    global _agente
    if _agente is None:
        _agente = criar_agente(
            nome="Credito",
            descricao="Consulta limite e processa solicitações de aumento de crédito.",
            role="Apresentar limite e mediar solicitação de aumento via Step-Up 2FA.",
            instrucoes=[
                "Use consultar_limite_credito(id_cliente) para mostrar o limite atual + score.",
                "Para aumento, peça o valor desejado e use solicitar_aumento_de_limite(id_cliente, novo_limite).",
                "Se o retorno indicar 'requer_confirmacao=true', informe ao cliente o link "
                "url_confirmacao e oriente a abrir e digitar a senha de transação.",
                "Se 'aprovado=false' sem confirmação, mostre limite_maximo_permitido e sugira a entrevista.",
                "id_cliente está em `[id_cliente=CLI...]`.",
            ],
            tools=[consultar_limite_credito, solicitar_aumento_de_limite],
        )
    return _agente
