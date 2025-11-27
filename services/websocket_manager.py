from fastapi import WebSocket
from typing import Dict

class ConexaoWebsocket:
    def __init__(self):
        self.conexao_ativa: Dict[str, WebSocket] = {}
    
    async def conexao(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.conexao_ativa[client_id] = websocket
    
    def desconexao(self, client_id: str):
        if client_id in self.conexao_ativa:
            del self.conexao_ativa[client_id]

    async def enviar_mensagem(self, client_id: str, mensagem: str):
        if client_id in self.conexao_ativa:
            websocket = self.conexao_ativa[client_id]
            await websocket.send_text(mensagem)

conexao_master = ConexaoWebsocket()