"""Rota de criação de transações (com Step-Up 2FA)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from assistente_bancario_v2.banking_gateway.app.core.auth_interno import (
    exigir_token_interno,
)
from assistente_bancario_v2.banking_gateway.app.domain.schemas import (
    RequisicaoTransacao,
    RespostaTransacao,
)
from assistente_bancario_v2.banking_gateway.app.services.transacao_service import (
    criar_transacao,
)

roteador = APIRouter(prefix="/transacao", tags=["Transações"])


@roteador.post(
    "", response_model=RespostaTransacao, dependencies=[Depends(exigir_token_interno)]
)
async def criar(req: RequisicaoTransacao) -> RespostaTransacao:
    resultado = await criar_transacao(
        id_cliente=req.id_cliente,
        tipo=req.tipo,
        descricao=req.descricao,
        valor=req.valor,
        data_vencimento=req.data_vencimento,
        chave_idempotencia=req.chave_idempotencia,
        nome_pagador=req.nome_pagador,
        data_prevista=req.data_prevista,
    )
    return RespostaTransacao(
        id_requisicao=resultado["id_requisicao"],
        status=resultado["status"],
        mensagem=resultado["mensagem"],
        criado_em=resultado["criado_em"],
        requer_confirmacao=resultado.get("requer_confirmacao", False),
        url_confirmacao=resultado.get("url_confirmacao"),
        token_confirmacao=resultado.get("token_confirmacao"),
    )
