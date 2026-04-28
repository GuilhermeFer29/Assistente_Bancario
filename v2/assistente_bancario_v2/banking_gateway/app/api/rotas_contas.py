"""Rotas de contas (a pagar / a receber / pagas / vencidas)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.core.auth_interno import (
    exigir_token_interno,
)
from assistente_bancario_v2.banking_gateway.app.db.database import obter_sessao
from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
    buscar_cliente,
    listar_contas,
)
from assistente_bancario_v2.banking_gateway.app.domain.schemas import (
    RespostaConta,
    RespostaListaContas,
)
from assistente_bancario_v2.banking_gateway.app.services.pagamento_service import (
    iniciar_pagamento_conta,
)


class RequisicaoPagarConta(BaseModel):
    id_cliente: str
    id_conta: str

_TIPOS_VALIDOS = {"a_vencer", "vencidas", "pagas"}

roteador = APIRouter(prefix="/contas", tags=["Contas"])


@roteador.get("/{id_cliente}", response_model=RespostaListaContas)
async def consultar_contas(
    id_cliente: str,
    tipo: str = Query("a_vencer", description="a_vencer | vencidas | pagas"),
    data_inicio: date | None = None,
    data_fim: date | None = None,
    sessao: AsyncSession = Depends(obter_sessao),
) -> RespostaListaContas:
    if tipo not in _TIPOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo inválido. Use um de: {sorted(_TIPOS_VALIDOS)}",
        )
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )

    contas = await listar_contas(
        sessao,
        id_cliente=id_cliente,
        tipo=tipo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    total_valor = sum((c.valor for c in contas), start=Decimal("0.00"))
    return RespostaListaContas(
        contas=[
            RespostaConta(
                id_conta=c.id_conta,
                id_cliente=c.id_cliente,
                descricao=c.descricao,
                valor=c.valor,
                data_vencimento=c.data_vencimento,
                status=c.status,
                tipo=c.tipo,
                nome_pagador=c.nome_pagador,
                data_prevista=c.data_prevista,
            )
            for c in contas
        ],
        total=len(contas),
        total_valor=total_valor,
    )


@roteador.post("/pagar", dependencies=[Depends(exigir_token_interno)])
async def pagar_conta(req: RequisicaoPagarConta) -> dict:  # type: ignore[type-arg]
    """Inicia pagamento de uma conta existente — gera Step-Up 2FA (rota interna)."""
    resultado = await iniciar_pagamento_conta(req.id_cliente, req.id_conta)
    if "erro" in resultado:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=resultado["erro"])
    return resultado
