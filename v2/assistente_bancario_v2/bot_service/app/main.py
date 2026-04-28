"""Bot Service — Chat web com agentes Agno (V2)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from assistente_bancario_v2.bot_service.app.core.config import configuracao_bot
from assistente_bancario_v2.bot_service.app.core.logging_config import (
    configurar_logging,
    logger,
)
from assistente_bancario_v2.bot_service.app.routes.ws_chat import roteador as roteador_chat


@asynccontextmanager
async def ciclo_vida(app: FastAPI) -> AsyncGenerator[None, None]:
    nivel = "DEBUG" if configuracao_bot.debug else configuracao_bot.log_level
    configurar_logging(nivel)
    logger.info(
        "iniciando_bot_service",
        ambiente=configuracao_bot.ambiente,
        gateway_transport=configuracao_bot.gateway_transport,
        gemini_configurado=bool(configuracao_bot.gemini_api_key),
    )
    yield
    logger.info("encerrando_bot_service")


app = FastAPI(
    title="Assistente Bancário V2 — Bot Service",
    description="Chat com agentes Agno (Triagem, Saldo, Contas, Transacoes, Credito, Entrevista, Cambio).",
    version="2.0.0",
    lifespan=ciclo_vida,
)

app.include_router(roteador_chat)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "servico": "bot_service"}
