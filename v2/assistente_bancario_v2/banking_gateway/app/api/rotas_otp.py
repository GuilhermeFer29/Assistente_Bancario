"""Rotas OTP por e-mail."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from assistente_bancario_v2.banking_gateway.app.core.auth_interno import (
    exigir_token_interno,
)
from assistente_bancario_v2.banking_gateway.app.core.rate_limit import limiter
from assistente_bancario_v2.banking_gateway.app.domain.schemas import (
    RequisicaoOtpIniciar,
    RequisicaoOtpValidar,
    RespostaOtpIniciar,
    RespostaOtpValidar,
)
from assistente_bancario_v2.banking_gateway.app.services.otp_service import (
    iniciar_otp,
    validar_otp,
)

roteador = APIRouter(prefix="/otp", tags=["OTP"])


@roteador.post(
    "/iniciar",
    response_model=RespostaOtpIniciar,
    dependencies=[Depends(exigir_token_interno)],
)
@limiter.limit("5/minute")
async def rota_iniciar(
    request: Request, req: RequisicaoOtpIniciar
) -> RespostaOtpIniciar:
    """Dispara OTP por e-mail (rota interna — exige X-Internal-Token)."""
    resultado = await iniciar_otp(req.id_cliente)
    return RespostaOtpIniciar(**resultado)


@roteador.post(
    "/validar",
    response_model=RespostaOtpValidar,
    dependencies=[Depends(exigir_token_interno)],
)
@limiter.limit("10/minute")
async def rota_validar(
    request: Request, req: RequisicaoOtpValidar
) -> RespostaOtpValidar:
    """Valida o código OTP (rota interna — exige X-Internal-Token)."""
    resultado = await validar_otp(req.id_cliente, req.codigo)
    return RespostaOtpValidar(
        valido=resultado["valido"],
        motivo=resultado.get("motivo"),
        nome=resultado.get("nome"),
    )
