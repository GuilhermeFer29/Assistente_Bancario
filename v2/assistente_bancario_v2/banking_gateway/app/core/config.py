"""Configuração do banking_gateway via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfiguracaoGateway(BaseSettings):
    """Configurações do banking_gateway (env vars)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    ambiente: str = "dev"
    debug: bool = False
    log_level: str = "INFO"

    # Banco de dados
    gateway_database_url: str = "sqlite+aiosqlite:///./data/gateway.db"

    # E-mail
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@bancoagil.local"
    smtp_tls: bool = False           # TLS implícito (port 465)
    smtp_starttls: bool = False      # STARTTLS (port 587 — Gmail/Outlook)

    # OTP
    otp_expiracao_min: int = 5
    otp_max_tentativas: int = 3
    otp_bloqueio_min: int = 15

    # Confirmação Step-Up
    confirmacao_expiracao_min: int = 10
    confirmacao_max_tentativas: int = 3

    # URLs públicas (montadas em links)
    gateway_public_url: str = "http://localhost:8001"

    # Token interno compartilhado entre bot ↔ gateway (rotas de criação de Step-Up
    # exigem este header para impedir uso externo direto). Em prod, gerar aleatório.
    internal_api_token: str = "dev-internal-token-please-change"


configuracao_gateway = ConfiguracaoGateway()
