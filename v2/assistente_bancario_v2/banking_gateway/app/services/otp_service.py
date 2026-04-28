"""Serviço de OTP por e-mail."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from assistente_bancario_v2.banking_gateway.app.core.config import configuracao_gateway
from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger
from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
from assistente_bancario_v2.banking_gateway.app.db.models import Cliente, Otp
from assistente_bancario_v2.banking_gateway.app.services.email_client import enviar_otp

_PH = PasswordHasher()


def _gerar_codigo() -> str:
    """6 dígitos numéricos."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _agora() -> datetime:
    return datetime.now(UTC)


async def iniciar_otp(id_cliente: str) -> dict[str, Any]:
    """Cria OTP, envia e-mail e SÓ persiste o registro se o e-mail saiu.

    Ordem de operações para evitar 'OTP queimado' (registro existe mas cliente
    não recebeu o código):
    1. Verifica cliente + bloqueio
    2. Gera código + hash em memória
    3. Tenta enviar e-mail
    4. Se enviado, abre nova sessão e persiste o OTP (invalidando os anteriores)
    """
    expira_em_iso = ""
    async with fabrica_sessao() as sessao:
        res = await sessao.execute(select(Cliente).where(Cliente.id_cliente == id_cliente))
        cliente = res.scalar_one_or_none()
        if cliente is None:
            return {"enviado": False, "mensagem": "Cliente não encontrado."}

        res = await sessao.execute(
            select(Otp)
            .where(Otp.id_cliente == id_cliente, Otp.consumido.is_(False))  # type: ignore[attr-defined]
            .order_by(Otp.criado_em.desc())
        )
        otp_atual = res.scalars().first()
        if (
            otp_atual is not None
            and otp_atual.bloqueado_ate is not None
            and otp_atual.bloqueado_ate > _agora().replace(tzinfo=None)
        ):
            return {
                "enviado": False,
                "mensagem": "Cliente temporariamente bloqueado. Tente mais tarde.",
            }

        email_dest = cliente.email
        nome = cliente.nome

    # 1) Gera código fora da sessão (ainda não persistimos)
    codigo = _gerar_codigo()
    codigo_hash = _PH.hash(codigo)
    expira_em_dt = _agora() + timedelta(minutes=configuracao_gateway.otp_expiracao_min)

    # 2) Tenta enviar e-mail. Só persiste se o envio for bem-sucedido.
    enviado = await enviar_otp(
        destinatario=email_dest,
        codigo=codigo,
        expiracao_min=configuracao_gateway.otp_expiracao_min,
    )
    if not enviado:
        logger.warning("otp_envio_falhou_sem_persistir", id_cliente=id_cliente, nome=nome)
        return {"enviado": False, "mensagem": "Falha ao enviar e-mail. Tente novamente."}

    # 3) Persiste — agora podemos invalidar OTPs anteriores e gravar o novo
    async with fabrica_sessao() as sessao:
        res = await sessao.execute(
            select(Otp)
            .where(Otp.id_cliente == id_cliente, Otp.consumido.is_(False))  # type: ignore[attr-defined]
            .order_by(Otp.criado_em.desc())
        )
        for otp_anterior in res.scalars():
            otp_anterior.consumido = True
            sessao.add(otp_anterior)

        novo = Otp(
            id_cliente=id_cliente,
            codigo_hash=codigo_hash,
            criado_em=_agora(),
            expira_em=expira_em_dt.replace(tzinfo=None),
        )
        sessao.add(novo)
        expira_em_iso = expira_em_dt.isoformat()

    logger.info("otp_iniciado", id_cliente=id_cliente)
    return {
        "enviado": True,
        "expira_em": expira_em_iso,
        "mensagem": "Código enviado por e-mail.",
    }


async def validar_otp(id_cliente: str, codigo: str) -> dict[str, Any]:
    """Valida OTP. Retorna {valido, motivo, nome}."""
    async with fabrica_sessao() as sessao:
        res = await sessao.execute(select(Cliente).where(Cliente.id_cliente == id_cliente))
        cliente = res.scalar_one_or_none()
        if cliente is None:
            return {"valido": False, "motivo": "cliente_nao_encontrado"}

        res = await sessao.execute(
            select(Otp)
            .where(Otp.id_cliente == id_cliente, Otp.consumido.is_(False))  # type: ignore[attr-defined]
            .order_by(Otp.criado_em.desc())
        )
        otp = res.scalars().first()
        if otp is None:
            return {"valido": False, "motivo": "sem_otp_pendente"}

        agora = _agora().replace(tzinfo=None)
        if otp.bloqueado_ate is not None and otp.bloqueado_ate > agora:
            return {"valido": False, "motivo": "bloqueado"}
        if otp.expira_em < agora:
            otp.consumido = True
            sessao.add(otp)
            return {"valido": False, "motivo": "expirado"}

        try:
            _PH.verify(otp.codigo_hash, codigo)
        except VerifyMismatchError:
            otp.tentativas += 1
            if otp.tentativas >= configuracao_gateway.otp_max_tentativas:
                otp.bloqueado_ate = agora + timedelta(
                    minutes=configuracao_gateway.otp_bloqueio_min
                )
                otp.consumido = True
                sessao.add(otp)
                logger.warning("otp_bloqueado_por_tentativas", id_cliente=id_cliente)
                return {"valido": False, "motivo": "bloqueado_tentativas"}
            sessao.add(otp)
            return {
                "valido": False,
                "motivo": "codigo_incorreto",
                "tentativas_restantes": (
                    configuracao_gateway.otp_max_tentativas - otp.tentativas
                ),
            }

        otp.consumido = True
        sessao.add(otp)
        logger.info("otp_validado", id_cliente=id_cliente)
        return {"valido": True, "nome": cliente.nome}
