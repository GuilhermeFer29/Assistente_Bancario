"""Engine SQLAlchemy async + factory de sessão."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from assistente_bancario_v2.banking_gateway.app.core.config import configuracao_gateway

_engine = create_async_engine(
    configuracao_gateway.gateway_database_url,
    echo=configuracao_gateway.debug,
    future=True,
)

_fabrica = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def inicializar_banco() -> None:
    """Cria todas as tabelas (no-op se já existem)."""
    # Importar aqui garante que os modelos estão registrados em SQLModel.metadata
    from assistente_bancario_v2.banking_gateway.app.db import models  # noqa: F401

    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def fabrica_sessao() -> AsyncGenerator[AsyncSession, None]:
    """Context manager que entrega uma sessão e garante commit/rollback."""
    async with _fabrica() as sessao:
        try:
            yield sessao
            await sessao.commit()
        except Exception:
            await sessao.rollback()
            raise


async def obter_sessao() -> AsyncGenerator[AsyncSession, None]:
    """Dependência FastAPI para injetar sessão (sem auto-commit)."""
    async with _fabrica() as sessao:
        yield sessao
