"""Serviço de transações com idempotência e Step-Up."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger
from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
from assistente_bancario_v2.banking_gateway.app.db.models import Transacao
from assistente_bancario_v2.banking_gateway.app.db.repositorio import buscar_cliente
from assistente_bancario_v2.packages.shared.constants import StatusTransacao


async def criar_transacao(
    *,
    id_cliente: str,
    tipo: str,
    descricao: str,
    valor: Decimal,
    data_vencimento: date | str,
    chave_idempotencia: str | None = None,
    nome_pagador: str | None = None,
    data_prevista: date | str | None = None,
) -> dict[str, Any]:
    """Inicia criação de transação. NÃO grava — emite Step-Up."""
    if isinstance(data_vencimento, str):
        data_vencimento = date.fromisoformat(data_vencimento)
    if isinstance(data_prevista, str):
        data_prevista = date.fromisoformat(data_prevista)

    if tipo not in {"a_pagar", "a_receber"}:
        return {"status": "erro", "mensagem": "Tipo inválido (a_pagar | a_receber)."}

    chave = chave_idempotencia or uuid4().hex

    # Sessão única: cliente exists + idempotência (atômico)
    async with fabrica_sessao() as sessao:
        cliente = await buscar_cliente(sessao, id_cliente)
        if cliente is None:
            return {"status": "erro", "mensagem": "Cliente não encontrado."}

        res = await sessao.execute(
            select(Transacao).where(Transacao.chave_idempotencia == chave)
        )
        existente = res.scalar_one_or_none()
        if existente is not None:
            return {
                "status": "duplicada",
                "id_requisicao": existente.id_requisicao,
                "mensagem": "Transação já registrada com esta chave de idempotência.",
                "criado_em": existente.criado_em.isoformat(),
            }

    # Emitir Step-Up
    from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
        criar_confirmacao,
    )

    dados = {
        "tipo": tipo,
        "descricao": descricao,
        "valor": str(valor),
        "data_vencimento": data_vencimento.isoformat(),
        "chave_idempotencia": chave,
        "nome_pagador": nome_pagador,
        "data_prevista": data_prevista.isoformat() if data_prevista else None,
    }
    confirmacao = await criar_confirmacao(
        id_cliente=id_cliente, operacao="criar_transacao", dados_operacao=dados
    )
    logger.info(
        "transacao_pendente_confirmacao",
        id_cliente=id_cliente,
        tipo=tipo,
        valor=str(valor),
    )
    return {
        "id_requisicao": chave,
        "status": "pendente_confirmacao",
        "mensagem": "Para confirmar, abra o link e digite sua senha.",
        "criado_em": datetime.now(UTC).isoformat(),
        "requer_confirmacao": True,
        "url_confirmacao": confirmacao["url"],
        "token_confirmacao": confirmacao["token"],
    }


async def executar_criacao_transacao(
    *, sessao: AsyncSession, id_cliente: str, dados: dict[str, Any]
) -> dict[str, Any]:
    """Executa a criação real da transação após Step-Up confirmado."""
    chave = dados["chave_idempotencia"]
    res = await sessao.execute(
        select(Transacao).where(Transacao.chave_idempotencia == chave)
    )
    if res.scalar_one_or_none() is not None:
        return {"aplicado": False, "motivo": "duplicada"}

    transacao = Transacao(
        id_requisicao=chave,
        id_cliente=id_cliente,
        chave_idempotencia=chave,
        tipo=dados["tipo"],
        descricao=dados["descricao"],
        valor=Decimal(str(dados["valor"])),
        data_vencimento=date.fromisoformat(dados["data_vencimento"]),
        status=StatusTransacao.CONFIRMADA.value,
    )
    sessao.add(transacao)
    await sessao.flush()
    logger.info(
        "transacao_criada", id_cliente=id_cliente, tipo=dados["tipo"], valor=dados["valor"]
    )
    return {
        "aplicado": True,
        "id_requisicao": transacao.id_requisicao,
        "valor": float(transacao.valor),
        "tipo": transacao.tipo,
    }
