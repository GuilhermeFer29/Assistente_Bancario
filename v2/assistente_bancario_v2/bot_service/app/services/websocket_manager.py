"""Gerenciador de conexões WebSocket por session_id."""

from __future__ import annotations

from fastapi import WebSocket


class GerenciadorWS:
    def __init__(self) -> None:
        self._conexoes: dict[str, WebSocket] = {}

    async def conectar(self, ws: WebSocket, session_id: str) -> None:
        await ws.accept()
        self._conexoes[session_id] = ws

    def desconectar(self, session_id: str) -> None:
        self._conexoes.pop(session_id, None)

    async def enviar(self, session_id: str, texto: str) -> None:
        ws = self._conexoes.get(session_id)
        if ws is not None:
            await ws.send_text(texto)


gerenciador = GerenciadorWS()
