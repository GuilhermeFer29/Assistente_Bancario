"""Ferramentas do gateway para os agentes Agno.

Padrão BANKPER:
- async def plain (sem closures, sem decoradores)
- type hints completos + docstring Google-style → Agno infere o schema
- retorno dict (sucesso) ou {"erro": "mensagem"} (falha)
- id_cliente vem do prefixo [id_cliente=X] que o orquestrador injeta na mensagem
"""

from __future__ import annotations

from datetime import date

from assistente_bancario_v2.bot_service.app.services.gateway_client import (
    obter_gateway_client,
)

# ── SALDO ──────────────────────────────────────────────────────


async def obter_saldo_cliente(id_cliente: str) -> dict:
    """Consulta o saldo bancário do cliente.

    Args:
        id_cliente: Identificador do cliente (ex: 'CLI901').

    Returns:
        dict com nome, saldo_disponivel, saldo_bloqueado, moeda, atualizado_em.
        Em caso de erro: {"erro": "..."}
    """
    gw = obter_gateway_client()
    dados = await gw.consultar_saldo(id_cliente)
    if not dados:
        return {"erro": "Não foi possível consultar o saldo. Cliente não encontrado."}
    return dados


# ── CONTAS ─────────────────────────────────────────────────────


async def obter_contas_cliente(
    id_cliente: str,
    tipo: str,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> dict:
    """Lista contas do cliente filtradas por tipo e período opcional.

    Args:
        id_cliente: Identificador do cliente (ex: 'CLI901').
        tipo: 'a_vencer', 'vencidas' ou 'pagas'.
        data_inicio: Data inicial YYYY-MM-DD (opcional).
        data_fim: Data final YYYY-MM-DD (opcional).

    Returns:
        dict com contas (lista), total e total_valor. Em erro: {"erro": "..."}
    """
    if tipo not in {"a_vencer", "vencidas", "pagas"}:
        return {"erro": "tipo inválido (use 'a_vencer', 'vencidas' ou 'pagas')."}
    d_ini = date.fromisoformat(data_inicio) if data_inicio else None
    d_fim = date.fromisoformat(data_fim) if data_fim else None

    gw = obter_gateway_client()
    dados = await gw.consultar_contas(id_cliente, tipo=tipo, data_inicio=d_ini, data_fim=d_fim)
    if not dados:
        return {"erro": f"Não foi possível listar contas {tipo}."}
    return dados


# ── CRÉDITO ────────────────────────────────────────────────────


async def consultar_limite_credito(id_cliente: str) -> dict:
    """Consulta o limite de crédito atual e o score do cliente.

    Args:
        id_cliente: Identificador do cliente.

    Returns:
        dict com nome, limite_atual, score. Em erro: {"erro": "..."}
    """
    gw = obter_gateway_client()
    dados = await gw.consultar_limite(id_cliente)
    if not dados:
        return {"erro": "Cliente não encontrado para consulta de limite."}
    return dados


async def solicitar_aumento_de_limite(id_cliente: str, novo_limite: float) -> dict:
    """Solicita aumento de limite. SEMPRE exige Step-Up (confirmação web).

    Args:
        id_cliente: Identificador do cliente.
        novo_limite: Valor desejado em reais (positivo).

    Returns:
        dict com requer_confirmacao=True e url_confirmacao quando aprovado;
        ou aprovado=False com motivo quando rejeitado pela faixa de score.
    """
    from decimal import Decimal

    gw = obter_gateway_client()
    return await gw.solicitar_aumento_limite(id_cliente, Decimal(str(novo_limite)))


async def atualizar_score_cliente(
    id_cliente: str,
    renda: float,
    tipo_emprego: str,
    despesas_mensais: float,
    dependentes: int,
    tem_dividas: str,
) -> dict:
    """Atualiza o score do cliente após entrevista financeira.

    Args:
        id_cliente: Identificador do cliente.
        renda: Renda mensal bruta (em reais).
        tipo_emprego: 'formal', 'autonomo' ou 'desempregado'.
        despesas_mensais: Despesas fixas mensais (em reais).
        dependentes: Quantidade de dependentes (>= 0).
        tem_dividas: 'sim' ou 'nao'.

    Returns:
        dict com sucesso e novo_score. Em erro: {"erro": "..."}
    """
    from decimal import Decimal

    gw = obter_gateway_client()
    return await gw.atualizar_score(
        id_cliente=id_cliente,
        renda=Decimal(str(renda)),
        tipo_emprego=tipo_emprego,
        despesas_mensais=Decimal(str(despesas_mensais)),
        dependentes=int(dependentes),
        tem_dividas=tem_dividas,
    )


# ── TRANSAÇÕES ─────────────────────────────────────────────────


async def criar_transacao_cliente(
    id_cliente: str,
    tipo: str,
    descricao: str,
    valor: float,
    data_vencimento: str,
    nome_pagador: str | None = None,
) -> dict:
    """Cria uma transação NOVA a pagar/receber (não existente nas contas). Step-Up.

    Use APENAS quando o cliente quer registrar um lançamento NOVO.
    Para pagar uma conta JÁ EXISTENTE da lista, use `pagar_conta`.

    Args:
        id_cliente: Identificador do cliente.
        tipo: 'a_pagar' ou 'a_receber'.
        descricao: Texto curto descrevendo a operação.
        valor: Valor em reais (positivo).
        data_vencimento: Data ISO YYYY-MM-DD.
        nome_pagador: Nome do pagador (apenas a_receber).

    Returns:
        dict com requer_confirmacao=True e url_confirmacao para o cliente.
    """
    from decimal import Decimal

    gw = obter_gateway_client()
    return await gw.criar_transacao(
        id_cliente=id_cliente,
        tipo=tipo,
        descricao=descricao,
        valor=Decimal(str(valor)),
        data_vencimento=data_vencimento,
        nome_pagador=nome_pagador,
    )


async def pagar_conta(id_cliente: str, id_conta: str) -> dict:
    """Inicia pagamento de uma conta JÁ existente — gera Step-Up 2FA.

    Quando confirmado pelo cliente na página web, a conta é marcada como PAGA
    e uma transação de auditoria é criada. Use SEMPRE que o cliente disser
    'pagar conta X' / 'pagar todas as contas' para itens já listados.

    Args:
        id_cliente: Identificador do cliente.
        id_conta: ID da conta retornada por `obter_contas_cliente`.

    Returns:
        dict com requer_confirmacao=True, url_confirmacao, descricao, valor.
        Em erro: {"erro": "..."}
    """
    gw = obter_gateway_client()
    return await gw.pagar_conta_existente(id_cliente, id_conta)
