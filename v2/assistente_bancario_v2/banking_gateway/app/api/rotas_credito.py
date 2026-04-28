"""Rotas de crédito (limite, aumento de limite via Step-Up, atualização de score)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.core.auth_interno import (
    exigir_token_interno,
)
from assistente_bancario_v2.banking_gateway.app.db.database import obter_sessao
from assistente_bancario_v2.banking_gateway.app.db.repositorio import buscar_cliente
from assistente_bancario_v2.banking_gateway.app.domain.schemas import (
    RequisicaoAtualizarScore,
    RequisicaoAumentoLimite,
    RespostaAtualizarScore,
    RespostaAumentoLimite,
    RespostaLimite,
)
from assistente_bancario_v2.banking_gateway.app.services.credito_service import (
    processar_atualizar_score,
    processar_solicitacao_aumento,
)

roteador = APIRouter(prefix="/credito", tags=["Crédito"])
_DEPS_INTERNAS = [Depends(exigir_token_interno)]


@roteador.get(
    "/limite/{id_cliente}",
    response_model=RespostaLimite,
    dependencies=_DEPS_INTERNAS,
)
async def consultar_limite(
    id_cliente: str, sessao: AsyncSession = Depends(obter_sessao)
) -> RespostaLimite:
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cliente não encontrado."
        )
    return RespostaLimite(
        id_cliente=cliente.id_cliente,
        nome=cliente.nome,
        limite_atual=cliente.limite_credito,
        score=cliente.score_credito,
    )


@roteador.post(
    "/solicitar-aumento",
    response_model=RespostaAumentoLimite,
    dependencies=_DEPS_INTERNAS,
)
async def solicitar_aumento(req: RequisicaoAumentoLimite) -> RespostaAumentoLimite:
    resultado = await processar_solicitacao_aumento(req.id_cliente, req.novo_limite)
    return RespostaAumentoLimite(
        aprovado=resultado.get("aprovado", False),
        requer_confirmacao=resultado.get("requer_confirmacao", False),
        url_confirmacao=resultado.get("url_confirmacao"),
        token_confirmacao=resultado.get("token_confirmacao"),
        novo_limite=resultado.get("novo_limite"),
        limite_maximo_permitido=resultado.get("limite_maximo_permitido"),
        mensagem=resultado.get("mensagem", ""),
    )


@roteador.post(
    "/atualizar-score",
    response_model=RespostaAtualizarScore,
    dependencies=_DEPS_INTERNAS,
)
async def atualizar_score(req: RequisicaoAtualizarScore) -> RespostaAtualizarScore:
    resultado = await processar_atualizar_score(
        id_cliente=req.id_cliente,
        renda=req.renda,
        tipo_emprego=req.tipo_emprego,
        despesas_mensais=req.despesas_mensais,
        dependentes=req.dependentes,
        tem_dividas=req.tem_dividas,
    )
    return RespostaAtualizarScore(
        sucesso=resultado.get("sucesso", False),
        novo_score=resultado.get("novo_score"),
        mensagem=resultado.get("mensagem", ""),
    )
