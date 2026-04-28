"""Testa as duas implementações do GatewayClient (in_process e http)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import select


@pytest.fixture
def banco_temporario(monkeypatch):  # type: ignore[no-untyped-def]
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    monkeypatch.setenv("GATEWAY_DATABASE_URL", f"sqlite+aiosqlite:///{tmp.name}")
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
async def gateway_pronto(banco_temporario):  # type: ignore[no-untyped-def]
    """Inicializa o banco do gateway, popula seed, retorna o id do primeiro cliente."""
    import importlib

    from assistente_bancario_v2.banking_gateway.app.core import config as _c
    importlib.reload(_c)
    from assistente_bancario_v2.banking_gateway.app.db import database as _db
    importlib.reload(_db)
    from assistente_bancario_v2.banking_gateway.app.db.models import Cliente
    from assistente_bancario_v2.banking_gateway.app.db.seed import executar_seed

    await _db.inicializar_banco()
    async with _db.fabrica_sessao() as sessao:
        await executar_seed(sessao)
    async with _db.fabrica_sessao() as sessao:
        cliente = (await sessao.execute(select(Cliente))).scalars().first()
    return cliente.id_cliente


@pytest.mark.asyncio
async def test_in_process_consulta_cliente(gateway_pronto, monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("GATEWAY_TRANSPORT", "in_process")
    import importlib

    from assistente_bancario_v2.bot_service.app.core import config as bot_config
    importlib.reload(bot_config)

    from assistente_bancario_v2.bot_service.app.services import gateway_client as gc
    importlib.reload(gc)
    gc.resetar_gateway_client()
    cliente_gw = gc.obter_gateway_client()

    info = await cliente_gw.consultar_cliente(gateway_pronto)
    assert info is not None
    assert info["id_cliente"] == gateway_pronto

    saldo = await cliente_gw.consultar_saldo(gateway_pronto)
    assert saldo is not None
    assert saldo["saldo_disponivel"] > 0

    contas = await cliente_gw.consultar_contas(gateway_pronto, tipo="a_vencer")
    assert contas is not None
    assert "contas" in contas


@pytest.mark.asyncio
async def test_in_process_cliente_inexistente_retorna_none(
    gateway_pronto, monkeypatch
):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("GATEWAY_TRANSPORT", "in_process")
    import importlib

    from assistente_bancario_v2.bot_service.app.core import config as bot_config
    importlib.reload(bot_config)
    from assistente_bancario_v2.bot_service.app.services import gateway_client as gc
    importlib.reload(gc)
    gc.resetar_gateway_client()

    cliente_gw = gc.obter_gateway_client()
    info = await cliente_gw.consultar_cliente("INEXISTENTE")
    assert info is None
