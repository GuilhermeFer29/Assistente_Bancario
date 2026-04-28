"""Orquestrador de mensagens — state machine de auth + delegação ao Team.

Fluxo:
    INICIO            → "ola, informe seu ID (ex: CLI901)"  → AGUARDANDO_ID
    AGUARDANDO_ID     → recebe ID, dispara OTP             → AGUARDANDO_OTP
    AGUARDANDO_OTP    → valida código                       → AUTENTICADO
    AUTENTICADO       → tudo via Team Agno (com prefixo [id_cliente=X])

A autenticação é determinística — não usa LLM. Só conversas pós-auth vão ao Team.
"""

from __future__ import annotations

import re

import structlog

from assistente_bancario_v2.bot_service.app.agents.team import obter_team
from assistente_bancario_v2.bot_service.app.services import sessao_estado
from assistente_bancario_v2.bot_service.app.services.gateway_client import (
    obter_gateway_client,
)
from assistente_bancario_v2.bot_service.app.services.sessao_estado import Etapa
from assistente_bancario_v2.packages.shared.utils import normalizar_cliente_id

logger = structlog.get_logger("orquestrador")

_REGEX_ID_CLIENTE = re.compile(r"^\s*(CLI\s?\d{1,6})\s*$", re.IGNORECASE)
_REGEX_CODIGO_OTP = re.compile(r"^\s*(\d{4,8})\s*$")


def _saudacao_inicial() -> str:
    return (
        "👋 Olá! Sou o **Rog**, seu assistente do Banco Ágil.\n\n"
        "Para começarmos, informe seu **ID de cliente** (ex: `CLI901`)."
    )


def _ja_autenticado(nome: str) -> str:
    return f"Você já está autenticado como **{nome}**. Como posso ajudá-lo?"


# ── State machine ───────────────────────────────────────────────


async def _processar_aguardando_id(session_id: str, texto: str) -> str:
    m = _REGEX_ID_CLIENTE.match(texto.strip())
    if not m:
        return (
            "Não reconheci esse formato. Por favor, informe o **ID de cliente** "
            "no formato `CLI` + 3 dígitos (ex: `CLI901`)."
        )

    cid = normalizar_cliente_id(m.group(1).replace(" ", ""))
    gw = obter_gateway_client()

    cliente = await gw.consultar_cliente(cid)
    if cliente is None:
        return (
            f"Não localizei o cliente `{cid}`. Confira o ID e tente novamente "
            "(ex: `CLI901`)."
        )

    # Tenta enviar OTP ANTES de marcar id_pendente — falha não corrompe estado
    resultado = await gw.iniciar_otp(cid)
    if not resultado.get("enviado"):
        # NÃO sobrescreve estado: continuamos em AGUARDANDO_ID para o cliente tentar de novo
        return (
            f"⚠️ Não foi possível enviar o código de verificação: "
            f"{resultado.get('mensagem', 'erro desconhecido')}. Tente novamente."
        )

    # Sucesso → atomicamente marca id_pendente + transição
    sessao_estado.set_kv(session_id, "id_cliente_pendente", cid)
    sessao_estado.set_kv(session_id, "nome_pendente", cliente.get("nome", ""))
    sessao_estado.set_etapa(session_id, Etapa.AGUARDANDO_OTP)
    nome = cliente.get("nome", cid)
    return (
        f"Olá, **{nome}**! Para sua segurança, enviei um **código de 6 dígitos** "
        f"para seu e-mail cadastrado.\n\nDigite o código aqui."
    )


async def _processar_aguardando_otp(session_id: str, texto: str) -> str:
    m = _REGEX_CODIGO_OTP.match(texto.strip())
    if not m:
        return (
            "Por favor, digite **apenas o código numérico** (4 a 8 dígitos) "
            "que você recebeu por e-mail."
        )

    estado = sessao_estado.get(session_id)
    cid = estado.get("id_cliente_pendente")
    if not cid:
        sessao_estado.set_etapa(session_id, Etapa.INICIO)
        return _saudacao_inicial()

    gw = obter_gateway_client()
    resultado = await gw.validar_otp(cid, m.group(1))
    if resultado.get("valido"):
        nome = resultado.get("nome") or estado.get("nome_pendente") or cid
        sessao_estado.marcar_autenticado(session_id, cid, nome)
        return (
            f"✅ **Autenticado com sucesso, {nome}!**\n\n"
            "Como posso ajudá-lo hoje? Posso auxiliar com:\n\n"
            "- Consultar **saldo** ou listar **contas a pagar/receber**\n"
            "- Consultar ou aumentar **limite de crédito**\n"
            "- **Entrevista** para melhorar seu score\n"
            "- **Cotações** de moedas estrangeiras\n"
            "- Criar uma **transação** a pagar ou a receber"
        )

    motivo = resultado.get("motivo", "")
    if motivo == "expirado":
        sessao_estado.set_etapa(session_id, Etapa.AGUARDANDO_ID)
        return "⌛ Código expirado. Informe novamente o ID de cliente para gerar um novo."
    if motivo in {"bloqueado", "bloqueado_tentativas"}:
        sessao_estado.set_etapa(session_id, Etapa.INICIO)
        return "🚫 Acesso bloqueado por excesso de tentativas. Tente novamente em 15 minutos."
    if motivo == "codigo_incorreto":
        tent = resultado.get("tentativas_restantes", "?")
        return f"❌ Código incorreto. Tentativas restantes: **{tent}**. Tente de novo."
    return f"⚠️ Não foi possível validar: {motivo or 'erro desconhecido'}."


async def _processar_autenticado(session_id: str, texto: str) -> str:
    team = obter_team()
    if team is None:
        return "⚠️ Os agentes não estão configurados (`GEMINI_API_KEY` ausente)."

    estado = sessao_estado.get(session_id)
    cid = estado.get("id_cliente")
    nome = estado.get("nome", "")

    # Padrão BANKPER: prefixo de contexto antes da mensagem real
    mensagem_com_contexto = f"[id_cliente={cid}] [nome={nome}]\n\n{texto}"

    try:
        resposta = await team.arun(  # type: ignore[attr-defined]
            mensagem_com_contexto, session_id=session_id, user_id=cid or session_id
        )
    except Exception:
        logger.exception("erro_team_arun", session_id=session_id)
        return "Desculpe, não consegui processar sua mensagem agora. Tente novamente."

    if hasattr(resposta, "content") and resposta.content:
        return str(resposta.content)
    return str(resposta)


# ── Entry point ────────────────────────────────────────────────


async def processar_mensagem(session_id: str, texto: str) -> str:
    """Decide o caminho conforme o estado atual da sessão."""
    etapa = sessao_estado.etapa(session_id)
    logger.info("orquestrador_in", session_id=session_id, etapa=etapa.value, tamanho=len(texto))

    if etapa == Etapa.INICIO:
        sessao_estado.set_etapa(session_id, Etapa.AGUARDANDO_ID)
        # Se a mensagem inicial parece um ID, processa direto
        if _REGEX_ID_CLIENTE.match(texto.strip()):
            return await _processar_aguardando_id(session_id, texto)
        return _saudacao_inicial()

    if etapa == Etapa.AGUARDANDO_ID:
        return await _processar_aguardando_id(session_id, texto)

    if etapa == Etapa.AGUARDANDO_OTP:
        return await _processar_aguardando_otp(session_id, texto)

    if etapa == Etapa.AUTENTICADO:
        return await _processar_autenticado(session_id, texto)

    sessao_estado.set_etapa(session_id, Etapa.INICIO)
    return _saudacao_inicial()


def encerrar_sessao(session_id: str) -> None:
    """Limpa o estado da sessão (botão 'nova conversa' do Streamlit)."""
    sessao_estado.limpar(session_id)
