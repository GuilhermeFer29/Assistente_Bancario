"""Rotas de clientes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.db.database import obter_sessao
from assistente_bancario_v2.banking_gateway.app.db.repositorio import buscar_cliente
from assistente_bancario_v2.banking_gateway.app.domain.schemas import (
    RespostaCliente,
    RespostaEmailCliente,
)

roteador = APIRouter(prefix="/clientes", tags=["Clientes"])


@roteador.get("/{id_cliente}", response_model=RespostaCliente)
async def consultar_cliente(
    id_cliente: str, sessao: AsyncSession = Depends(obter_sessao)
) -> RespostaCliente:
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )
    return RespostaCliente(
        id_cliente=cliente.id_cliente,
        nome=cliente.nome,
        email=cliente.email,
        telefone=cliente.telefone,
        confiavel=cliente.confiavel,
        ativo=cliente.ativo,
    )


@roteador.get("/{id_cliente}/email", response_model=RespostaEmailCliente)
async def consultar_email_cliente(
    id_cliente: str, sessao: AsyncSession = Depends(obter_sessao)
) -> RespostaEmailCliente:
    """Endpoint interno usado pelo bot para buscar e-mail antes de enviar OTP."""
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )
    return RespostaEmailCliente(id_cliente=cliente.id_cliente, email=cliente.email)
