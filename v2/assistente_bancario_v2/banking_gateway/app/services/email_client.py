"""Cliente SMTP async para envio de OTP e notificações.

Suporta três modos:
- Plain (Mailpit em dev)            → port 1025, sem TLS, sem auth
- STARTTLS (Gmail / Outlook 587)    → port 587, com auth, start_tls=True
- TLS implícito (Gmail SSL 465)     → port 465, com auth, use_tls=True
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from assistente_bancario_v2.banking_gateway.app.core.config import configuracao_gateway
from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger


def _from_header() -> str:
    """Define o cabeçalho From de forma compatível com provedores reais.

    Provedores como Gmail rejeitam um From de domínio diferente do user
    autenticado. Quando há SMTP_USER e o SMTP_FROM aponta para outro
    domínio, usamos SMTP_USER como remetente.
    """
    cfg = configuracao_gateway
    if cfg.smtp_user and "@" in cfg.smtp_user:
        from_dom = cfg.smtp_from.rsplit("@", 1)[-1] if "@" in cfg.smtp_from else ""
        user_dom = cfg.smtp_user.rsplit("@", 1)[-1]
        if from_dom != user_dom:
            return f"Banco Ágil <{cfg.smtp_user}>"
    return cfg.smtp_from


async def enviar_email(destinatario: str, assunto: str, corpo: str) -> bool:
    """Envia um e-mail simples (texto). Em DEBUG, loga ao invés de enviar."""
    cfg = configuracao_gateway

    if cfg.debug or not destinatario:
        # Em DEBUG NÃO logamos o corpo (contém OTP em plaintext).
        # Para inspecionar OTP em dev: consulte a tabela `otps` ou use Mailpit.
        logger.info(
            "email_dev_log",
            destinatario=destinatario,
            assunto=assunto,
            tamanho_corpo=len(corpo),
        )
        return True

    msg = EmailMessage()
    msg["From"] = _from_header()
    msg["To"] = destinatario
    msg["Subject"] = assunto
    msg.set_content(corpo)

    # Auto-detecção razoável: porta 587 → STARTTLS, porta 465 → TLS implícito
    porta = cfg.smtp_port
    use_tls = cfg.smtp_tls or porta == 465
    start_tls = cfg.smtp_starttls or (porta == 587 and not use_tls)

    try:
        await aiosmtplib.send(
            msg,
            hostname=cfg.smtp_host,
            port=porta,
            username=cfg.smtp_user or None,
            password=cfg.smtp_password or None,
            use_tls=use_tls,
            start_tls=start_tls,
            timeout=15,
        )
        logger.info(
            "email_enviado",
            destinatario=destinatario,
            assunto=assunto,
            host=cfg.smtp_host,
            porta=porta,
            modo="tls" if use_tls else ("starttls" if start_tls else "plain"),
        )
        return True
    except Exception as e:
        logger.error(
            "email_falhou",
            destinatario=destinatario,
            erro=str(e),
            host=cfg.smtp_host,
            porta=porta,
            use_tls=use_tls,
            start_tls=start_tls,
            assunto=assunto,
        )
        return False


async def enviar_otp(destinatario: str, codigo: str, expiracao_min: int) -> bool:
    """Envia o OTP por e-mail."""
    assunto = "Banco Ágil — Código de verificação"
    corpo = (
        f"Olá!\n\n"
        f"Seu código de verificação é: {codigo}\n\n"
        f"Este código expira em {expiracao_min} minutos.\n"
        f"Se não foi você, ignore esta mensagem.\n\n"
        f"— Equipe Banco Ágil"
    )
    return await enviar_email(destinatario, assunto, corpo)
