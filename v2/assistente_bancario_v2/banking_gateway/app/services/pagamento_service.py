"""Pagamento de contas existentes — gera Step-Up e quita a conta na confirmação."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger
from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
from assistente_bancario_v2.banking_gateway.app.db.models import Conta, Transacao
from assistente_bancario_v2.banking_gateway.app.db.repositorio import buscar_cliente
from assistente_bancario_v2.packages.shared.constants import StatusConta, StatusTransacao


async def iniciar_pagamento_conta(id_cliente: str, id_conta: str) -> dict[str, Any]:
    """Verifica conta + cria token de confirmação Step-Up.

    Operação: 'pagar_conta'. Dados contêm id_conta, descricao, valor, vencimento.
    """
    async with fabrica_sessao() as sessao:
        cliente = await buscar_cliente(sessao, id_cliente)
        if cliente is None:
            return {"erro": "Cliente não encontrado."}

        res = await sessao.execute(
            select(Conta).where(Conta.id_conta == id_conta, Conta.id_cliente == id_cliente)
        )
        conta = res.scalar_one_or_none()
        if conta is None:
            return {"erro": f"Conta {id_conta} não encontrada para este cliente."}
        if conta.status == StatusConta.PAGA.value:
            return {"erro": "Esta conta já está paga."}
        if conta.status == StatusConta.CANCELADA.value:
            return {"erro": "Esta conta foi cancelada."}

        dados = {
            "id_conta": conta.id_conta,
            "descricao": conta.descricao,
            "valor": str(conta.valor),
            "data_vencimento": conta.data_vencimento.isoformat(),
            "tipo": conta.tipo,
            "chave_idempotencia": uuid4().hex,
        }

    # Cria Step-Up
    from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
        criar_confirmacao,
    )

    confirmacao = await criar_confirmacao(
        id_cliente=id_cliente, operacao="pagar_conta", dados_operacao=dados
    )
    logger.info(
        "pagamento_conta_pendente_confirmacao",
        id_cliente=id_cliente,
        id_conta=id_conta,
        valor=dados["valor"],
    )
    return {
        "id_conta": id_conta,
        "descricao": conta.descricao,
        "valor": dados["valor"],
        "data_vencimento": dados["data_vencimento"],
        "tipo": conta.tipo,
        "requer_confirmacao": True,
        "url_confirmacao": confirmacao["url"],
        "token_confirmacao": confirmacao["token"],
        "mensagem": (
            f"Para pagar a conta '{conta.descricao}' "
            f"(R$ {float(conta.valor):.2f}), abra o link e digite a senha."
        ),
    }


async def executar_pagamento_conta(
    *, sessao: AsyncSession, id_cliente: str, dados: dict[str, Any]
) -> dict[str, Any]:
    """Confirma pagamento — marca conta PAGA + insere Transacao com idempotência."""
    id_conta = dados["id_conta"]
    chave = dados["chave_idempotencia"]

    res = await sessao.execute(
        select(Conta).where(Conta.id_conta == id_conta, Conta.id_cliente == id_cliente)
    )
    conta = res.scalar_one_or_none()
    if conta is None:
        return {"aplicado": False, "motivo": "conta_nao_encontrada"}

    # Idempotência da transacao
    res_tx = await sessao.execute(select(Transacao).where(Transacao.chave_idempotencia == chave))
    if res_tx.scalar_one_or_none() is not None:
        return {"aplicado": False, "motivo": "duplicada", "id_conta": id_conta}

    # Marca conta como PAGA
    conta.status = StatusConta.PAGA.value
    sessao.add(conta)

    # Cria transacao (auditoria do pagamento)
    transacao = Transacao(
        id_requisicao=chave,
        id_cliente=id_cliente,
        chave_idempotencia=chave,
        tipo=conta.tipo,
        descricao=f"Pagamento: {conta.descricao}",
        valor=conta.valor,
        data_vencimento=conta.data_vencimento,
        status=StatusTransacao.CONFIRMADA.value,
    )
    sessao.add(transacao)
    await sessao.flush()

    logger.info(
        "pagamento_conta_executado",
        id_cliente=id_cliente,
        id_conta=id_conta,
        valor=str(conta.valor),
    )
    return {
        "aplicado": True,
        "id_conta": id_conta,
        "descricao": conta.descricao,
        "valor": float(conta.valor),
        "tipo": conta.tipo,
    }
