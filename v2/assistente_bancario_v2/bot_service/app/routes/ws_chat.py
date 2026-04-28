"""WebSocket de chat — delega ao orquestrador (state machine + Team)."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from assistente_bancario_v2.bot_service.app.services.orquestrador import (
    encerrar_sessao,
    processar_mensagem,
)
from assistente_bancario_v2.bot_service.app.services.websocket_manager import gerenciador
from assistente_bancario_v2.packages.shared.constants import STREAM_END_TOKEN

roteador = APIRouter(prefix="/chat", tags=["Chat"])
logger = structlog.get_logger("ws_chat")


@roteador.websocket("/ws/{session_id}")
async def chat_ws(websocket: WebSocket, session_id: str) -> None:
    await gerenciador.conectar(websocket, session_id)
    logger.info("ws_conectado", session_id=session_id)
    try:
        while True:
            mensagem = await websocket.receive_text()
            try:
                resposta = await processar_mensagem(session_id, mensagem)
            except Exception as exc:  # noqa: BLE001
                logger.error("ws_erro", session_id=session_id, erro=str(exc))
                resposta = "Desculpe, ocorreu um erro. Tente novamente."

            if resposta and resposta.strip():
                await gerenciador.enviar(session_id, resposta)
            await gerenciador.enviar(session_id, STREAM_END_TOKEN)
    except WebSocketDisconnect:
        logger.info("ws_desconectado", session_id=session_id)
    except Exception as exc:  # noqa: BLE001
        logger.error("ws_erro_inesperado", session_id=session_id, erro=str(exc))
    finally:
        # NÃO limpa o estado — sobrevive entre conexões (Streamlit abre WS por mensagem)
        gerenciador.desconectar(session_id)


@roteador.post("/encerrar/{session_id}")
async def rota_encerrar(session_id: str) -> dict[str, str]:
    """Limpa o estado da sessão (botão 'Nova conversa' do Streamlit)."""
    encerrar_sessao(session_id)
    logger.info("sessao_encerrada", session_id=session_id)
    return {"status": "ok", "session_id": session_id}
