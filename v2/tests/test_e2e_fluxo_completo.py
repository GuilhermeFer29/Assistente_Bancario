"""Simulação E2E do fluxo completo do bot — varre todos os caminhos.

Não usa Gemini real. Mocka o Team.arun() para retornar respostas determinísticas
e verifica o resto do pipeline (state machine, tools, gateway, persistência, Step-Up).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select


@pytest.fixture(autouse=True)
def _ambiente(monkeypatch):  # type: ignore[no-untyped-def]
    """Banco temporário + transporte in_process + DEBUG (silencia SMTP)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    bot_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    bot_tmp.close()

    monkeypatch.setenv("GATEWAY_DATABASE_URL", f"sqlite+aiosqlite:///{tmp.name}")
    monkeypatch.setenv("BOT_DATABASE_URL", f"sqlite+aiosqlite:///{bot_tmp.name}")
    monkeypatch.setenv("AGNO_DB_FILE", bot_tmp.name)
    monkeypatch.setenv("GATEWAY_TRANSPORT", "in_process")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "internal-token-test-only")

    # Reload configs e DB
    import importlib

    from assistente_bancario_v2.banking_gateway.app.core import config as gw_cfg
    importlib.reload(gw_cfg)
    from assistente_bancario_v2.banking_gateway.app.db import database as gw_db
    importlib.reload(gw_db)
    from assistente_bancario_v2.bot_service.app.core import config as bot_cfg
    importlib.reload(bot_cfg)
    from assistente_bancario_v2.bot_service.app.services import gateway_client as gc
    importlib.reload(gc)
    gc.resetar_gateway_client()
    from assistente_bancario_v2.bot_service.app.services import sessao_estado
    sessao_estado._estado.clear()  # noqa: SLF001

    yield

    Path(tmp.name).unlink(missing_ok=True)
    Path(bot_tmp.name).unlink(missing_ok=True)


@pytest.fixture
async def gateway_pronto():  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.db.database import (
        fabrica_sessao,
        inicializar_banco,
    )
    from assistente_bancario_v2.banking_gateway.app.db.seed import executar_seed

    await inicializar_banco()
    async with fabrica_sessao() as sessao:
        await executar_seed(sessao)


# ──────────────────────────────────────────────────────────────────
# Fluxo 1: Login completo (state machine pura)
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fluxo_login_completo_e2e(gateway_pronto, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Saudação → ID → OTP → AUTENTICADO."""
    from assistente_bancario_v2.banking_gateway.app.services import otp_service
    from assistente_bancario_v2.bot_service.app.services import sessao_estado
    from assistente_bancario_v2.bot_service.app.services.orquestrador import (
        processar_mensagem,
    )

    # Forçar OTP previsível
    monkeypatch.setattr(otp_service, "_gerar_codigo", lambda: "111222")

    sid = "S_E2E_LOGIN"

    r1 = await processar_mensagem(sid, "olá")
    assert "ID de cliente" in r1
    assert sessao_estado.etapa(sid).value == "AGUARDANDO_ID"

    r2 = await processar_mensagem(sid, "CLI901")
    assert "código" in r2.lower() or "Guilherme" in r2
    assert sessao_estado.etapa(sid).value == "AGUARDANDO_OTP"

    r3 = await processar_mensagem(sid, "111222")
    assert "Autenticado" in r3 or "autenticado" in r3.lower()
    assert sessao_estado.autenticado(sid)
    assert sessao_estado.cliente_id(sid) == "CLI901"


@pytest.mark.asyncio
async def test_fluxo_login_id_inexistente_e2e(gateway_pronto) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.bot_service.app.services.orquestrador import (
        processar_mensagem,
    )

    sid = "S_E2E_INEXISTENTE"
    await processar_mensagem(sid, "olá")
    r = await processar_mensagem(sid, "CLI999")
    assert "Não localizei" in r


@pytest.mark.asyncio
async def test_fluxo_login_otp_3_tentativas_bloqueia(
    gateway_pronto, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.services import otp_service
    from assistente_bancario_v2.bot_service.app.services import sessao_estado
    from assistente_bancario_v2.bot_service.app.services.orquestrador import (
        processar_mensagem,
    )

    monkeypatch.setattr(otp_service, "_gerar_codigo", lambda: "999000")
    sid = "S_E2E_BLOQUEIO"

    await processar_mensagem(sid, "olá")
    await processar_mensagem(sid, "CLI901")

    for _ in range(2):
        await processar_mensagem(sid, "000000")
    final = await processar_mensagem(sid, "000000")
    assert "bloqueado" in final.lower()
    assert sessao_estado.etapa(sid).value == "INICIO"


# ──────────────────────────────────────────────────────────────────
# Fluxo 2: Tools post-auth (chamadas reais ao gateway in_process)
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tool_obter_saldo_e2e(gateway_pronto) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        obter_saldo_cliente,
    )

    saldo = await obter_saldo_cliente("CLI901")
    assert "erro" not in saldo
    assert saldo["nome"] == "Guilherme Fernandes"
    assert float(saldo["saldo_disponivel"]) > 0


@pytest.mark.asyncio
async def test_tool_obter_contas_a_vencer_e2e(gateway_pronto) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        obter_contas_cliente,
    )

    r = await obter_contas_cliente("CLI901", tipo="a_vencer")
    assert "erro" not in r
    assert r["total"] >= 1
    assert all("id_conta" in c for c in r["contas"])


@pytest.mark.asyncio
async def test_tool_consultar_limite_e2e(gateway_pronto) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        consultar_limite_credito,
    )

    r = await consultar_limite_credito("CLI901")
    assert "erro" not in r
    assert "limite_atual" in r
    assert "score" in r


# ──────────────────────────────────────────────────────────────────
# Fluxo 3: Aumento de limite com Step-Up E2E
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_aumento_limite_dentro_faixa_emite_step_up(
    gateway_pronto,
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        solicitar_aumento_de_limite,
    )

    r = await solicitar_aumento_de_limite("CLI901", 6000.00)
    assert r["requer_confirmacao"] is True
    assert "/confirmar/" in r["url_confirmacao"]


@pytest.mark.asyncio
async def test_aumento_limite_acima_faixa_rejeita(
    gateway_pronto,
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        solicitar_aumento_de_limite,
    )

    r = await solicitar_aumento_de_limite("CLI901", 99999.00)
    assert r["aprovado"] is False
    assert r["requer_confirmacao"] is False
    assert r["limite_maximo_permitido"] is not None


# ──────────────────────────────────────────────────────────────────
# Fluxo 4: Pagar conta existente E2E (Step-Up + persistência)
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pagar_conta_e2e_marca_paga(gateway_pronto) -> None:  # type: ignore[no-untyped-def]
    """Tool pagar_conta → confirmar via service → conta vira PAGA."""
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
    from assistente_bancario_v2.banking_gateway.app.db.models import Conta
    from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
        validar_e_executar,
    )
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        obter_contas_cliente,
        pagar_conta,
    )
    from assistente_bancario_v2.packages.shared.constants import StatusConta

    contas = await obter_contas_cliente("CLI901", tipo="a_vencer")
    a_pagar = next(c for c in contas["contas"] if c["tipo"] == "a_pagar")
    id_conta = a_pagar["id_conta"]

    r = await pagar_conta("CLI901", id_conta)
    assert r["requer_confirmacao"] is True
    token = r["token_confirmacao"]

    res = await validar_e_executar(token, "1234")
    assert res["sucesso"] is True

    async with fabrica_sessao() as sessao:
        conta = (
            await sessao.execute(select(Conta).where(Conta.id_conta == id_conta))
        ).scalar_one()
        assert conta.status == StatusConta.PAGA.value


# ──────────────────────────────────────────────────────────────────
# Fluxo 5: Atualização de score (entrevista)
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_entrevista_score_atualiza_e2e(
    gateway_pronto,
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
    from assistente_bancario_v2.banking_gateway.app.db.models import Cliente
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        atualizar_score_cliente,
        consultar_limite_credito,
    )

    score_antes = (await consultar_limite_credito("CLI901"))["score"]

    r = await atualizar_score_cliente(
        id_cliente="CLI901",
        renda=10000.0,
        tipo_emprego="formal",
        despesas_mensais=2000.0,
        dependentes=0,
        tem_dividas="nao",
    )
    assert r["sucesso"] is True
    assert isinstance(r["novo_score"], int)
    assert 0 <= r["novo_score"] <= 1000

    # Confirma persistência no banco
    async with fabrica_sessao() as sessao:
        cliente = (
            await sessao.execute(select(Cliente).where(Cliente.id_cliente == "CLI901"))
        ).scalar_one()
        assert cliente.score_credito == r["novo_score"]
        assert cliente.score_credito != score_antes  # mudou


# ──────────────────────────────────────────────────────────────────
# Fluxo 6: Step-Up — cenários defensivos
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_step_up_senha_errada_3x_rejeita(
    gateway_pronto,
) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
        validar_e_executar,
    )
    from assistente_bancario_v2.bot_service.app.tools.gateway_tools import (
        solicitar_aumento_de_limite,
    )

    r = await solicitar_aumento_de_limite("CLI901", 6000.00)
    token = r["token_confirmacao"]

    for _ in range(2):
        res = await validar_e_executar(token, "errada")
        assert res["sucesso"] is False

    # Terceira tentativa errada → REJEITADA
    res_final = await validar_e_executar(token, "errada")
    assert res_final["sucesso"] is False

    # Tentar a senha CORRETA depois do bloqueio → não funciona
    res_pos = await validar_e_executar(token, "1234")
    assert res_pos["sucesso"] is False
    assert "rejeitada" in res_pos["motivo"].lower()


@pytest.mark.asyncio
async def test_step_up_token_invalido(gateway_pronto) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.services.confirmacao_service import (
        validar_e_executar,
    )

    r = await validar_e_executar("token_inexistente_xxxxx", "1234")
    assert r["sucesso"] is False
    assert r["motivo"] == "token_invalido"


# ──────────────────────────────────────────────────────────────────
# Fluxo 7: Memória cross-agent (compartilhada via SqliteDb)
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agentes_compartilham_db_singleton() -> None:
    """Validação técnica: todos os agentes usam o MESMO SqliteDb."""
    os.environ["GEMINI_API_KEY"] = "fake-key"
    from assistente_bancario_v2.bot_service.app.agents.team import obter_team

    team = obter_team()
    assert team is not None
    assert len(team.members) == 6
    db_id = id(team.db)
    for m in team.members:
        assert id(m.db) == db_id, f"{m.name} não compartilha SqliteDb com Team"


# ──────────────────────────────────────────────────────────────────
# Fluxo 8: Encerramento e re-conexão de sessão
# ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_encerrar_e_reiniciar_sessao(gateway_pronto, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from assistente_bancario_v2.banking_gateway.app.services import otp_service
    from assistente_bancario_v2.bot_service.app.services import sessao_estado
    from assistente_bancario_v2.bot_service.app.services.orquestrador import (
        encerrar_sessao,
        processar_mensagem,
    )

    monkeypatch.setattr(otp_service, "_gerar_codigo", lambda: "555666")
    sid = "S_RECONEXAO"

    await processar_mensagem(sid, "olá")
    await processar_mensagem(sid, "CLI901")
    await processar_mensagem(sid, "555666")
    assert sessao_estado.autenticado(sid)

    encerrar_sessao(sid)
    assert sessao_estado.etapa(sid).value == "INICIO"

    # Pode iniciar de novo limpo
    r = await processar_mensagem(sid, "olá")
    assert "ID de cliente" in r
