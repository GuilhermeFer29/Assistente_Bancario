"""Autenticação interna entre bot_service ↔ banking_gateway.

Rotas que criam ou alteram estado SENSÍVEL (Step-Up, pagar conta, aumentar limite)
exigem o header `X-Internal-Token` igual a `INTERNAL_API_TOKEN`. Isso evita que
um terceiro acesse o gateway diretamente via rede e gere tokens de Step-Up.

Em prod: trocar `INTERNAL_API_TOKEN` por um valor aleatório forte e propagar
ao bot via secret manager.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException, status


def _token_esperado() -> str:
    """Lê o token a cada request (suporta reload de config nos testes)."""
    # Ler do env diretamente — evita capturar instância stale após reload
    return (
        os.environ.get("INTERNAL_API_TOKEN")
        or _carregar_via_config()
    )


def _carregar_via_config() -> str:
    """Fallback: lê via pydantic-settings (caso env não esteja propagado)."""
    from assistente_bancario_v2.banking_gateway.app.core.config import (
        configuracao_gateway,
    )

    return configuracao_gateway.internal_api_token


async def exigir_token_interno(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    """Dependência FastAPI — bloqueia se o token não bater."""
    esperado = _token_esperado()
    if not esperado:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token interno não configurado.",
        )
    if x_internal_token != esperado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token interno inválido.",
        )
