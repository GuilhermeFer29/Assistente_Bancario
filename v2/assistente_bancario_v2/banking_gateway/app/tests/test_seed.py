"""Testa o seed do gateway: idempotência e contagens mínimas."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from assistente_bancario_v2.banking_gateway.app.db.models import (
    Cliente,
    Conta,
    Saldo,
    ScoreCreditoBase,
)


@pytest.mark.asyncio
async def test_seed_carrega_score_e_clientes(app_gateway) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao

    async with fabrica_sessao() as sessao:
        score = (await sessao.execute(select(ScoreCreditoBase))).scalars().all()
        clientes = (await sessao.execute(select(Cliente))).scalars().all()
        saldos = (await sessao.execute(select(Saldo))).scalars().all()
        contas = (await sessao.execute(select(Conta))).scalars().all()

    assert len(score) >= 1, "score_credito_base deve ter ao menos 1 faixa"
    assert len(clientes) >= 1, "deve haver clientes"
    assert len(saldos) == len(clientes), "1 saldo por cliente"
    # 6 contas (3 a_pagar + 3 a_receber) por cliente
    assert len(contas) == 6 * len(clientes)


@pytest.mark.asyncio
async def test_seed_eh_idempotente(app_gateway) -> None:  # type: ignore[no-untyped-def]
    """Rodar o seed duas vezes não duplica registros."""
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
    from assistente_bancario_v2.banking_gateway.app.db.seed import executar_seed

    async with fabrica_sessao() as sessao:
        antes_clientes = len((await sessao.execute(select(Cliente))).scalars().all())
        antes_contas = len((await sessao.execute(select(Conta))).scalars().all())

    async with fabrica_sessao() as sessao:
        await executar_seed(sessao)

    async with fabrica_sessao() as sessao:
        depois_clientes = len((await sessao.execute(select(Cliente))).scalars().all())
        depois_contas = len((await sessao.execute(select(Conta))).scalars().all())

    assert antes_clientes == depois_clientes
    assert antes_contas == depois_contas


@pytest.mark.asyncio
async def test_endpoint_cliente_404_quando_nao_existe(app_gateway) -> None:  # type: ignore[no-untyped-def]
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as cliente:
        resp = await cliente.get("/clientes/INEXISTENTE")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_endpoints_basicos_para_cliente_real(app_gateway) -> None:  # type: ignore[no-untyped-def]
    """Pega o primeiro cliente do seed e bate /clientes /saldo /contas."""
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao

    async with fabrica_sessao() as sessao:
        cliente_obj = (
            (await sessao.execute(select(Cliente))).scalars().first()
        )
        assert cliente_obj is not None
        id_cliente = cliente_obj.id_cliente

    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r1 = await http.get(f"/clientes/{id_cliente}")
        assert r1.status_code == 200
        assert r1.json()["id_cliente"] == id_cliente
        assert "@" in r1.json()["email"]

        r2 = await http.get(f"/saldo/{id_cliente}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["id_cliente"] == id_cliente
        assert float(body["saldo_disponivel"]) > 0

        r3 = await http.get(f"/contas/{id_cliente}", params={"tipo": "a_vencer"})
        assert r3.status_code == 200
        listagem = r3.json()
        assert "contas" in listagem
        assert listagem["total"] >= 0


@pytest.mark.asyncio
async def test_endpoint_contas_tipo_invalido(app_gateway) -> None:  # type: ignore[no-untyped-def]
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r = await http.get("/contas/CLI001", params={"tipo": "errado"})
        assert r.status_code == 400
