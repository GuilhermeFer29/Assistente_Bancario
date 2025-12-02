from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import conexao_master
from agent.agents import processar_mensagem, limpar_sessao
from agent.constants import STREAM_END_TOKEN
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def extrair_conteudo_streaming(evento) -> str:
    """Extrai o conteúdo de texto de um evento de streaming do Agno."""
    if evento is None:
        return ""
    
    # Agno RunResponseEvent tem atributo 'content'
    if hasattr(evento, 'content') and evento.content:
        return str(evento.content)
    
    # Fallback para outros formatos
    if hasattr(evento, 'data'):
        return str(evento.data)
    if hasattr(evento, 'text'):
        return str(evento.text)
    
    # Último recurso
    texto = str(evento)
    if texto and texto.strip() and texto != "None":
        return texto
    
    return ""


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Endpoint WebSocket para chat com o agente do Banco Ágil."""
    await conexao_master.conexao(websocket, client_id)
    logger.info(f"WebSocket conectado: {client_id}")

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Mensagem recebida de {client_id}: {data[:50]}...")
            
            try:
                # Usar stream=False para simplificar e garantir respostas completas
                is_stream, payload = processar_mensagem(client_id, data, stream=False)
                
                if is_stream and hasattr(payload, '__iter__') and not isinstance(payload, str):
                    # Processar streaming - acumular resposta completa
                    resposta_completa = []
                    for evento in payload:
                        conteudo = extrair_conteudo_streaming(evento)
                        if conteudo:
                            resposta_completa.append(conteudo)
                    
                    # Enviar resposta completa de uma vez
                    texto_final = "".join(resposta_completa)
                    if texto_final.strip():
                        await conexao_master.enviar_mensagem(client_id, texto_final)
                else:
                    # Resposta simples (sem streaming)
                    resposta = str(payload) if payload else "Desculpe, não consegui processar sua mensagem."
                    if resposta.strip():
                        await conexao_master.enviar_mensagem(client_id, resposta)

                # Enviar token de fim de streaming
                await conexao_master.enviar_mensagem(client_id, STREAM_END_TOKEN)
                
            except Exception as e:
                logger.error(f"Erro processando mensagem de {client_id}: {str(e)}")
                await conexao_master.enviar_mensagem(client_id, f"Desculpe, ocorreu um erro. Por favor, tente novamente.")
                await conexao_master.enviar_mensagem(client_id, STREAM_END_TOKEN)
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket desconectado: {client_id}")
        limpar_sessao(client_id)
        conexao_master.desconexao(client_id)
    except Exception as e:
        logger.error(f"Erro na conexão WebSocket {client_id}: {str(e)}")
        limpar_sessao(client_id)
        conexao_master.desconexao(client_id)