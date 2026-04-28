"""Configuração do bot_service via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracaoBot(BaseSettings):
    """Configurações do bot_service (env vars)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ambiente: str = "dev"
    debug: bool = False
    log_level: str = "INFO"

    # LLM
    gemini_api_key: str = ""
    tavily_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # Transporte ao gateway
    gateway_transport: str = "in_process"  # in_process | http
    gateway_url: str = "http://localhost:8001"

    # Banco de dados (sessões Agno)
    bot_database_url: str = "sqlite+aiosqlite:///./data/bot.db"
    agno_db_file: str = "./data/bot.db"

    # WebSocket / streaming
    stream_enabled: bool = False

    # URLs (para Streamlit)
    bot_ws_url: str = "ws://localhost:8000/chat/ws"
    gateway_public_url: str = "http://localhost:8001"

    # Token interno enviado no header X-Internal-Token ao gateway
    internal_api_token: str = "dev-internal-token-please-change"


configuracao_bot = ConfiguracaoBot()
