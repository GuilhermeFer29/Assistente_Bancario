"""Schemas Pydantic compartilhados (transporte WS, respostas comuns)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventoEntrada(BaseModel):
    """Mensagem recebida pelo bot_service via WebSocket."""

    session_id: str
    texto: str
    correlacao: str = ""


class RespostaPadrao(BaseModel):
    """Envelope padrão de resposta (sucesso/erro)."""

    sucesso: bool
    dados: Any | None = None
    erro: str | None = None
    metadados: dict[str, Any] = Field(default_factory=dict)
