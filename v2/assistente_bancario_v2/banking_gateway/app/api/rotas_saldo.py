"""Rota de saldo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.db.database import obter_sessao
from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
    buscar_cliente,
    buscar_saldo,
)
from assistente_bancario_v2.banking_gateway.app.domain.schemas import RespostaSaldo

roteador = APIRouter(prefix="/saldo", tags=["Saldo"])


@roteador.get("/{id_cliente}", response_model=RespostaSaldo)
async def consultar_saldo(
    id_cliente: str, sessao: AsyncSession = Depends(obter_sessao)
) -> RespostaSaldo:
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )
    saldo = await buscar_saldo(sessao, id_cliente)
    if saldo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Saldo não encontrado."
        )
    return RespostaSaldo(
        id_cliente=saldo.id_cliente,
        nome=cliente.nome,
        saldo_disponivel=saldo.saldo_disponivel,
        saldo_bloqueado=saldo.saldo_bloqueado,
        atualizado_em=saldo.atualizado_em,
    )
