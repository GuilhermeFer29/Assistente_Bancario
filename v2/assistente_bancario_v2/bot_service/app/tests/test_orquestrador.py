"""Testes da state machine de autenticação no orquestrador.

Não usa LLM — só os caminhos determinísticos (INICIO → AGUARDANDO_ID →
AGUARDANDO_OTP → AUTENTICADO). Mocka o gateway_client para isolar.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from assistente_bancario_v2.bot_service.app.services import sessao_estado
from assistente_bancario_v2.bot_service.app.services.orquestrador import (
    encerrar_sessao,
    processar_mensagem,
)
from assistente_bancario_v2.bot_service.app.services.sessao_estado import Etapa


@pytest.fixture(autouse=True)
def _limpar_estado() -> None:
    """Limpa estado de sessão entre testes."""
    sessao_estado._estado.clear()  # noqa: SLF001
    yield
    sessao_estado._estado.clear()  # noqa: SLF001


@pytest.fixture
def gateway_mock():
    """Mocka o gateway_client global do orquestrador."""
    fake = AsyncMock()
    with patch(
        "assistente_bancario_v2.bot_service.app.services.orquestrador.obter_gateway_client",
        return_value=fake,
    ):
        yield fake


@pytest.mark.asyncio
async def test_saudacao_inicial_quando_inicio(gateway_mock) -> None:
    resposta = await processar_mensagem("S1", "olá")
    assert "ID de cliente" in resposta
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_ID


@pytest.mark.asyncio
async def test_id_invalido_pede_novamente(gateway_mock) -> None:
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_ID)
    resposta = await processar_mensagem("S1", "abc123")
    assert "Não reconheci" in resposta
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_ID


@pytest.mark.asyncio
async def test_id_inexistente_no_gateway(gateway_mock) -> None:
    gateway_mock.consultar_cliente.return_value = None
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_ID)

    resposta = await processar_mensagem("S1", "CLI999")
    assert "Não localizei" in resposta
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_ID


@pytest.mark.asyncio
async def test_id_valido_dispara_otp(gateway_mock) -> None:
    gateway_mock.consultar_cliente.return_value = {"nome": "Guilherme", "id_cliente": "CLI901"}
    gateway_mock.iniciar_otp.return_value = {"enviado": True, "mensagem": "ok"}
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_ID)

    resposta = await processar_mensagem("S1", "CLI901")
    assert "Guilherme" in resposta
    assert "código" in resposta.lower()
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_OTP


@pytest.mark.asyncio
async def test_falha_envio_otp_mantem_aguardando_id(gateway_mock) -> None:
    """Falha no envio NÃO derruba a sessão — usuário pode tentar de novo."""
    gateway_mock.consultar_cliente.return_value = {"nome": "X", "id_cliente": "CLI901"}
    gateway_mock.iniciar_otp.return_value = {"enviado": False, "mensagem": "smtp falhou"}
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_ID)

    resposta = await processar_mensagem("S1", "CLI901")
    assert "smtp falhou" in resposta
    # Continua em AGUARDANDO_ID — cliente pode tentar de novo
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_ID
    # id_cliente_pendente NÃO é gravado em caso de falha
    assert sessao_estado.get("S1").get("id_cliente_pendente") is None


@pytest.mark.asyncio
async def test_otp_correto_marca_autenticado(gateway_mock) -> None:
    gateway_mock.validar_otp.return_value = {"valido": True, "nome": "Guilherme"}
    sessao_estado.set_kv("S1", "id_cliente_pendente", "CLI901")
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_OTP)

    resposta = await processar_mensagem("S1", "123456")
    assert "Autenticado" in resposta or "autenticado" in resposta.lower()
    assert sessao_estado.autenticado("S1")
    assert sessao_estado.cliente_id("S1") == "CLI901"


@pytest.mark.asyncio
async def test_otp_incorreto_decrementa_tentativas(gateway_mock) -> None:
    gateway_mock.validar_otp.return_value = {
        "valido": False,
        "motivo": "codigo_incorreto",
        "tentativas_restantes": 2,
    }
    sessao_estado.set_kv("S1", "id_cliente_pendente", "CLI901")
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_OTP)

    resposta = await processar_mensagem("S1", "000000")
    assert "incorreto" in resposta.lower()
    assert "2" in resposta
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_OTP


@pytest.mark.asyncio
async def test_otp_expirado_volta_para_id(gateway_mock) -> None:
    gateway_mock.validar_otp.return_value = {"valido": False, "motivo": "expirado"}
    sessao_estado.set_kv("S1", "id_cliente_pendente", "CLI901")
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_OTP)

    resposta = await processar_mensagem("S1", "123456")
    assert "expirado" in resposta.lower()
    assert sessao_estado.etapa("S1") == Etapa.AGUARDANDO_ID


@pytest.mark.asyncio
async def test_otp_bloqueado_volta_inicio(gateway_mock) -> None:
    gateway_mock.validar_otp.return_value = {"valido": False, "motivo": "bloqueado_tentativas"}
    sessao_estado.set_kv("S1", "id_cliente_pendente", "CLI901")
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_OTP)

    resposta = await processar_mensagem("S1", "000000")
    assert "bloqueado" in resposta.lower()
    assert sessao_estado.etapa("S1") == Etapa.INICIO


@pytest.mark.asyncio
async def test_codigo_otp_nao_numerico_pede_de_novo(gateway_mock) -> None:
    sessao_estado.set_kv("S1", "id_cliente_pendente", "CLI901")
    sessao_estado.set_etapa("S1", Etapa.AGUARDANDO_OTP)

    resposta = await processar_mensagem("S1", "abc")
    assert "código numérico" in resposta.lower() or "numérico" in resposta.lower()
    gateway_mock.validar_otp.assert_not_called()


@pytest.mark.asyncio
async def test_encerrar_sessao_limpa_estado(gateway_mock) -> None:
    sessao_estado.marcar_autenticado("S1", "CLI901", "X")
    encerrar_sessao("S1")
    assert sessao_estado.etapa("S1") == Etapa.INICIO
    assert sessao_estado.cliente_id("S1") is None
