"""Testa o fluxo completo de pagar uma conta existente."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def _primeira_conta_a_vencer():  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
    from assistente_bancario_v2.banking_gateway.app.db.models import Cliente, Conta
    from assistente_bancario_v2.packages.shared.constants import StatusConta

    async with fabrica_sessao() as sessao:
        cliente = (await sessao.execute(select(Cliente))).scalars().first()
        assert cliente is not None
        res = await sessao.execute(
            select(Conta).where(
                Conta.id_cliente == cliente.id_cliente,
                Conta.status == StatusConta.PENDENTE.value,
                Conta.tipo == "a_pagar",
            )
        )
        conta = res.scalars().first()
        assert conta is not None
        return cliente.id_cliente, conta.id_conta, str(conta.valor), conta.descricao


@pytest.mark.asyncio
async def test_pagar_conta_marca_como_paga_e_cria_transacao(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
    from assistente_bancario_v2.banking_gateway.app.db.models import Conta, Transacao
    from assistente_bancario_v2.packages.shared.constants import StatusConta

    id_cliente, id_conta, valor, descricao = await _primeira_conta_a_vencer()

    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        # 1) Inicia pagamento
        r = await http.post(
            "/contas/pagar", json={"id_cliente": id_cliente, "id_conta": id_conta}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["requer_confirmacao"] is True
        token = body["token_confirmacao"]
        assert "/confirmar/" in body["url_confirmacao"]

        # 2) Página HTML carrega
        r2 = await http.get(f"/confirmar/{token}")
        assert r2.status_code == 200
        assert descricao in r2.text or "pagar" in r2.text.lower()

        # 3) Confirma com senha correta (seed: "1234")
        r3 = await http.post(f"/confirmar/{token}", data={"senha": "1234"})
        assert r3.status_code == 200
        assert "sucesso" in r3.text.lower() or "confirmada" in r3.text.lower()

    # 4) Conta deve estar PAGA agora
    async with fabrica_sessao() as sessao:
        conta = (
            await sessao.execute(select(Conta).where(Conta.id_conta == id_conta))
        ).scalar_one()
        assert conta.status == StatusConta.PAGA.value

        # 5) Transacao de auditoria deve existir
        tx = (
            await sessao.execute(
                select(Transacao).where(Transacao.id_cliente == id_cliente)
            )
        ).scalars().all()
        assert any(str(t.valor) == valor for t in tx), "Transação de auditoria não criada"


@pytest.mark.asyncio
async def test_pagar_conta_idempotente_apos_confirmada(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    """Tentar pagar a mesma conta já paga deve retornar erro."""
    id_cliente, id_conta, _, _ = await _primeira_conta_a_vencer()

    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        # 1) Paga uma vez
        r = await http.post(
            "/contas/pagar", json={"id_cliente": id_cliente, "id_conta": id_conta}
        )
        token = r.json()["token_confirmacao"]
        r2 = await http.post(f"/confirmar/{token}", data={"senha": "1234"})
        assert r2.status_code == 200

        # 2) Tentar iniciar novo pagamento da mesma conta → erro
        r3 = await http.post(
            "/contas/pagar", json={"id_cliente": id_cliente, "id_conta": id_conta}
        )
        assert r3.status_code == 400
        assert "paga" in r3.json()["detail"].lower()


@pytest.mark.asyncio
async def test_pagar_conta_inexistente_retorna_400(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r = await http.post(
            "/contas/pagar", json={"id_cliente": "CLI901", "id_conta": "FAKE_NAO_EXISTE"}
        )
        assert r.status_code == 400


@pytest.mark.asyncio
async def test_apos_pagamento_conta_aparece_em_pagas(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    """Após pagar, a conta sai de a_vencer e entra em pagas."""
    id_cliente, id_conta, _, _ = await _primeira_conta_a_vencer()

    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        # Paga
        r = await http.post(
            "/contas/pagar", json={"id_cliente": id_cliente, "id_conta": id_conta}
        )
        token = r.json()["token_confirmacao"]
        await http.post(f"/confirmar/{token}", data={"senha": "1234"})

        # Lista a_vencer — id_conta NÃO deve estar
        r2 = await http.get(f"/contas/{id_cliente}", params={"tipo": "a_vencer"})
        ids_a_vencer = [c["id_conta"] for c in r2.json()["contas"]]
        assert id_conta not in ids_a_vencer

        # Lista pagas — id_conta DEVE estar
        r3 = await http.get(f"/contas/{id_cliente}", params={"tipo": "pagas"})
        ids_pagas = [c["id_conta"] for c in r3.json()["contas"]]
        assert id_conta in ids_pagas
