"""Banking Gateway — API fictícia de dados bancários (V2)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from assistente_bancario_v2.banking_gateway.app.api.rotas_clientes import (
    roteador as roteador_clientes,
)
from assistente_bancario_v2.banking_gateway.app.api.rotas_confirmacao import (
    roteador as roteador_confirmacao,
)
from assistente_bancario_v2.banking_gateway.app.api.rotas_contas import (
    roteador as roteador_contas,
)
from assistente_bancario_v2.banking_gateway.app.api.rotas_credito import (
    roteador as roteador_credito,
)
from assistente_bancario_v2.banking_gateway.app.api.rotas_otp import (
    roteador as roteador_otp,
)
from assistente_bancario_v2.banking_gateway.app.api.rotas_saldo import (
    roteador as roteador_saldo,
)
from assistente_bancario_v2.banking_gateway.app.api.rotas_transacao import (
    roteador as roteador_transacao,
)
from assistente_bancario_v2.banking_gateway.app.core.config import configuracao_gateway
from assistente_bancario_v2.banking_gateway.app.core.logging_config import (
    configurar_logging,
    logger,
)
from assistente_bancario_v2.banking_gateway.app.core.rate_limit import limiter
from assistente_bancario_v2.banking_gateway.app.db.database import (
    fabrica_sessao,
    inicializar_banco,
)
from assistente_bancario_v2.banking_gateway.app.db.seed import executar_seed

_STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def ciclo_vida(app: FastAPI) -> AsyncGenerator[None, None]:
    nivel = "DEBUG" if configuracao_gateway.debug else configuracao_gateway.log_level
    configurar_logging(nivel)
    logger.info("iniciando_banking_gateway", ambiente=configuracao_gateway.ambiente)

    await inicializar_banco()
    async with fabrica_sessao() as sessao:
        await executar_seed(sessao)

    yield
    logger.info("encerrando_banking_gateway")


app = FastAPI(
    title="Assistente Bancário V2 — Banking Gateway",
    description="API fictícia de dados bancários (clientes, saldo, contas, OTP, crédito, transações, confirmações).",
    version="2.0.0",
    lifespan=ciclo_vida,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(roteador_clientes)
app.include_router(roteador_saldo)
app.include_router(roteador_contas)
app.include_router(roteador_credito)
app.include_router(roteador_otp)
app.include_router(roteador_transacao)
app.include_router(roteador_confirmacao)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "servico": "banking_gateway"}
