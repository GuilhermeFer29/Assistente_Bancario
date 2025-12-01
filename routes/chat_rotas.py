from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import conexao_master
from agent.agents import processar_mensagem, limpar_sessoes_team
from agent.constants import STREAM_END_TOKEN
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/{client_id}")
# Função assíncrona para gerenciar conexões WebSocket
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Rota do websocket chat com Team Agno"""
    await conexao_master.conexao(websocket, client_id)
    logger.info(f"WebSocket conectado: {client_id}")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Mensagem recebida de {client_id}: {data[:50]}...")
            
            try:
                is_stream, payload = processar_mensagem(client_id, data, stream=True)

                if not is_stream:
                    # Resposta simples (sem streaming)
                    await conexao_master.enviar_mensagem(client_id, str(payload))
                else:
                    # Streaming do Agno - iterar sobre o generator corretamente
                    if hasattr(payload, '__iter__') and not isinstance(payload, str):
                        for evento in payload:
                            # Agno RunResponse tem atributo 'content'
                            if hasattr(evento, 'content'):
                                conteudo = str(evento.content)
                            elif hasattr(evento, 'data'):
                                conteudo = str(evento.data)
                            elif hasattr(evento, 'text'):
                                conteudo = str(evento.text)
                            else:
                                # Fallback para string do evento
                                conteudo = str(evento)
                            
                            if conteudo and conteudo.strip():
                                await conexao_master.enviar_mensagem(client_id, conteudo)
                    else:
                        # Se não for iterável, enviar como string simples
                        await conexao_master.enviar_mensagem(client_id, str(payload))

                # Enviar token de fim de streaming
                await conexao_master.enviar_mensagem(client_id, STREAM_END_TOKEN)
                
            except Exception as e:
                logger.error(f"Erro processando mensagem de {client_id}: {str(e)}")
                await conexao_master.enviar_mensagem(client_id, f"Erro ao processar: {str(e)}")
                await conexao_master.enviar_mensagem(client_id, STREAM_END_TOKEN)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado: {client_id}")
        conexao_master.desconexao(client_id)
    except Exception as e:
        logger.error(f"Erro na conexão WebSocket {client_id}: {str(e)}")
        await conexao_master.enviar_mensagem(client_id, f"Erro na conexão: {str(e)}")
        conexao_master.desconexao(client_id)