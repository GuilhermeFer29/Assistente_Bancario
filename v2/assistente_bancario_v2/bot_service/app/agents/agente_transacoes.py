"""Agente Transacoes — paga contas existentes ou cria transações novas (com Step-Up)."""

from __future__ import annotations

from agno.agent import Agent

from assistente_bancario_v2.bot_service.app.agents.agente_base import criar_agente
from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
    criar_transacao_cliente,
    obter_contas_cliente,
    pagar_conta,
)

_agente: Agent | None = None


def obter() -> Agent | None:
    global _agente
    if _agente is None:
        _agente = criar_agente(
            nome="Transacoes",
            descricao=(
                "Paga contas existentes (que aparecem na lista de contas a pagar) "
                "OU cria transações novas — sempre via Step-Up 2FA."
            ),
            role="Mediar pagamento de contas existentes e criação de transações novas.",
            instrucoes=[
                "## DUAS TAREFAS DISTINTAS",
                "",
                "### A) PAGAR CONTAS JÁ EXISTENTES (na lista do cliente)",
                "Use SEMPRE que o cliente disser 'pagar conta X', 'pagar todas as contas',",
                "'quitar conta', 'pagar #1' etc. para itens que JÁ aparecem como contas a pagar.",
                "",
                "Fluxo:",
                "1. Chame obter_contas_cliente(id_cliente, tipo='a_vencer') para pegar a lista atualizada (com id_conta).",
                "2. Identifique quais contas o cliente quer pagar (todas? algumas? por descrição/número?).",
                "3. Para CADA conta selecionada, chame pagar_conta(id_cliente, id_conta).",
                "4. O retorno traz url_confirmacao — copie a URL exata na resposta.",
                "5. Liste tudo em ordem: descrição, valor, link.",
                "",
                "### B) CRIAR TRANSAÇÃO NOVA (lançamento que ainda não existe)",
                "Use APENAS quando o cliente quer registrar uma operação NOVA, como",
                "'criar uma transação a receber de 500 reais' (não está na lista).",
                "",
                "Fluxo:",
                "1. Pergunte tipo (a_pagar/a_receber), descrição, valor, data_vencimento (YYYY-MM-DD).",
                "2. Para a_receber, peça também nome_pagador.",
                "3. Chame criar_transacao_cliente(id_cliente, tipo, descricao, valor, data_vencimento, nome_pagador?).",
                "4. Mostre a url_confirmacao.",
                "",
                "## REGRAS",
                "- id_cliente vem de `[id_cliente=CLI...]` no prefixo da mensagem.",
                "- NUNCA confirme pagamento — só após o cliente abrir o link e digitar a senha.",
                "- Se duplicada, informe que já foi registrada.",
            ],
            tools=[obter_contas_cliente, pagar_conta, criar_transacao_cliente],
            num_history_runs=15,
        )
    return _agente
