"""Fixtures comuns dos testes do banking_gateway."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


_TOKEN_DE_TESTE = "internal-token-test-only"

# Header padrão usado em todas as chamadas httpx dos testes.
HEADERS_INTERNOS = {"X-Internal-Token": _TOKEN_DE_TESTE}


@pytest.fixture
def banco_temporario(monkeypatch: pytest.MonkeyPatch) -> Generator[str, None, None]:
    """Aponta o gateway para um banco SQLite efêmero por teste."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    url = f"sqlite+aiosqlite:///{tmp.name}"
    monkeypatch.setenv("GATEWAY_DATABASE_URL", url)
    monkeypatch.setenv("INTERNAL_API_TOKEN", _TOKEN_DE_TESTE)
    yield url
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
async def app_gateway(banco_temporario: str) -> AsyncGenerator:
    """Importa o app com env já configurado e roda lifecycle."""
    # Forçar reload da config e do engine para que peguem o env do teste
    import importlib

    from assistente_bancario_v2.banking_gateway.app.core import config as _config_mod

    importlib.reload(_config_mod)

    from assistente_bancario_v2.banking_gateway.app.db import database as _db_mod

    importlib.reload(_db_mod)

    from assistente_bancario_v2.banking_gateway.app import main as _main_mod

    importlib.reload(_main_mod)

    # Trigger lifespan manualmente
    async with _main_mod.app.router.lifespan_context(_main_mod.app):
        yield _main_mod.app
