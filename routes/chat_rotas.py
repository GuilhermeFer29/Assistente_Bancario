from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import conexao_master
from agent.agents import secao_agente, limpar_sessoes_agentes

router = APIRouter()

@router.websocket("/ws/{client_id}")
# Função assíncrona para gerenciar conexões WebSocket
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Rota do websocket chat"""
    await conexao_master.conexao(websocket, client_id)

    agent = secao_agente(client_id)

    try:
        while True:
            data = await websocket.receive_text()
            resposta = agent.run(data, stream=False)
            await conexao_master.enviar_mensagem(client_id, resposta.content)
    except WebSocketDisconnect:
        """Encerra a conexão e limpa a sessão do agente ao desconectar"""
        conexao_master.desconexao(client_id)
        limpar_sessoes_agentes(client_id)
    except Exception as e:
        """Trata outras exceções e envia uma mensagem de erro ao cliente"""
        await conexao_master.enviar_mensagem(client_id, f"Erro no servidor: {str(e)}")
        conexao_master.desconexao(client_id)