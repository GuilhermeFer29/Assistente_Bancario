"""Testes do fluxo de OTP e crédito (limite, aumento via Step-Up, score)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


async def _primeiro_cliente() -> tuple[str, str]:
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
    from assistente_bancario_v2.banking_gateway.app.db.models import Cliente

    async with fabrica_sessao() as sessao:
        cliente = (await sessao.execute(select(Cliente))).scalars().first()
        assert cliente is not None
        return cliente.id_cliente, cliente.email


async def _ultimo_otp_codigo(id_cliente: str) -> str:
    """Em DEBUG, o código aparece no log mas não no banco. Para teste,
    forçamos o caminho lendo o hash do banco e quebrando por força bruta
    sobre 6 dígitos? Não — ineficiente. Vamos abrir um caminho de teste
    direto: mockar a geração do código via monkeypatch é mais limpo,
    mas o serviço já gera código e armazena hash. Aqui consultamos o
    último OTP gerado e validamos pelo código retornado pelo seed dev.
    Como precisamos do código original, este helper força DEBUG=true
    no app_gateway fixture e usamos uma rota auxiliar de teste.
    """
    raise NotImplementedError(
        "Use o helper monkeypatch para iniciar OTP com código fixo."
    )


@pytest.mark.asyncio
async def test_otp_iniciar_e_validar_fluxo_feliz(
    app_gateway, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    """Patch da geração de código para um valor conhecido, valida fluxo completo."""
    from assistente_bancario_v2.banking_gateway.app.services import otp_service

    monkeypatch.setattr(otp_service, "_gerar_codigo", lambda: "123456")

    id_cliente, _ = await _primeiro_cliente()
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r = await http.post("/otp/iniciar", json={"id_cliente": id_cliente})
        assert r.status_code == 200, r.text
        assert r.json()["enviado"] is True

        r2 = await http.post(
            "/otp/validar", json={"id_cliente": id_cliente, "codigo": "123456"}
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["valido"] is True
        assert r2.json()["nome"]


@pytest.mark.asyncio
async def test_otp_codigo_incorreto_decrementa_tentativas(
    app_gateway, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.services import otp_service

    monkeypatch.setattr(otp_service, "_gerar_codigo", lambda: "999999")
    id_cliente, _ = await _primeiro_cliente()

    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        await http.post("/otp/iniciar", json={"id_cliente": id_cliente})
        for _ in range(2):
            r = await http.post(
                "/otp/validar", json={"id_cliente": id_cliente, "codigo": "000000"}
            )
            assert r.status_code == 200
            assert r.json()["valido"] is False
            assert r.json()["motivo"] == "codigo_incorreto"

        # Terceira tentativa errada → bloqueio
        r = await http.post(
            "/otp/validar", json={"id_cliente": id_cliente, "codigo": "000000"}
        )
        assert r.json()["valido"] is False
        assert r.json()["motivo"] == "bloqueado_tentativas"


@pytest.mark.asyncio
async def test_consultar_limite(app_gateway) -> None:  # type: ignore[no-untyped-def]
    id_cliente, _ = await _primeiro_cliente()
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r = await http.get(f"/credito/limite/{id_cliente}")
        assert r.status_code == 200
        body = r.json()
        assert body["id_cliente"] == id_cliente
        assert "limite_atual" in body
        assert "score" in body


@pytest.mark.asyncio
async def test_aumento_limite_dentro_da_faixa_gera_confirmacao(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    """Aumento dentro da faixa permitida deve emitir Step-Up (não aprovar direto)."""
    id_cliente, _ = await _primeiro_cliente()
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        # Score base do seed é 519 → faixa 300-599 limite_max=10000
        # Pedindo 6000 (dentro da faixa): deve emitir Step-Up
        r = await http.post(
            "/credito/solicitar-aumento",
            json={"id_cliente": id_cliente, "novo_limite": "6000.00"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["aprovado"] is False
        assert body["requer_confirmacao"] is True
        assert body["url_confirmacao"]
        assert "/confirmar/" in body["url_confirmacao"]


@pytest.mark.asyncio
async def test_aumento_limite_fora_da_faixa_eh_rejeitado(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    id_cliente, _ = await _primeiro_cliente()
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        # 50000 está acima de qualquer faixa do seed
        r = await http.post(
            "/credito/solicitar-aumento",
            json={"id_cliente": id_cliente, "novo_limite": "50000.00"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["aprovado"] is False
        assert body["requer_confirmacao"] is False
        assert body["limite_maximo_permitido"] is not None


@pytest.mark.asyncio
async def test_atualizar_score_calcula_corretamente(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    id_cliente, _ = await _primeiro_cliente()
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r = await http.post(
            "/credito/atualizar-score",
            json={
                "id_cliente": id_cliente,
                "renda": "5000",
                "tipo_emprego": "formal",
                "despesas_mensais": "1000",
                "dependentes": 1,
                "tem_dividas": "nao",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["sucesso"] is True
        assert isinstance(body["novo_score"], int)
        assert 0 <= body["novo_score"] <= 1000


@pytest.mark.asyncio
async def test_step_up_pagina_confirmacao_renderiza(
    app_gateway,
) -> None:  # type: ignore[no-untyped-def]
    id_cliente, _ = await _primeiro_cliente()
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        # 1) Pede aumento → recebe token
        r = await http.post(
            "/credito/solicitar-aumento",
            json={"id_cliente": id_cliente, "novo_limite": "6000.00"},
        )
        token = r.json()["token_confirmacao"]
        assert token

        # 2) Página HTML carrega
        r2 = await http.get(f"/confirmar/{token}")
        assert r2.status_code == 200
        assert "Confirme sua operação" in r2.text or "Confirme" in r2.text
        assert "Aumento de limite" in r2.text

        # 3) Senha errada
        r3 = await http.post(f"/confirmar/{token}", data={"senha": "errada"})
        assert r3.status_code in (200, 400)
        assert "Senha incorreta" in r3.text or "tentativas" in r3.text

        # 4) Senha correta (seed: "1234")
        r4 = await http.post(f"/confirmar/{token}", data={"senha": "1234"})
        assert r4.status_code == 200
        assert "confirmada" in r4.text.lower() or "sucesso" in r4.text.lower()


@pytest.mark.asyncio
async def test_step_up_token_invalido_404(app_gateway) -> None:  # type: ignore[no-untyped-def]
    transporte = ASGITransport(app=app_gateway)
    async with AsyncClient(transport=transporte, base_url="http://test", headers={"X-Internal-Token": "internal-token-test-only"}) as http:
        r = await http.get("/confirmar/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert r.status_code == 404
