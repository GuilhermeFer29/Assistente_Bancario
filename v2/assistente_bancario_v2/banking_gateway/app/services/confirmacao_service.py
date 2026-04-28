"""Serviço de confirmação Step-Up 2FA via página web."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4


def _redigir_token(token: str) -> str:
    """Hash curto do token — para log sem revelar o valor real."""
    return hashlib.sha256(token.encode()).hexdigest()[:12]

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select

from assistente_bancario_v2.banking_gateway.app.core.config import configuracao_gateway
from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger
from assistente_bancario_v2.banking_gateway.app.db.database import fabrica_sessao
from assistente_bancario_v2.banking_gateway.app.db.models import (
    Cliente,
    ConfirmacaoPendente,
)
from assistente_bancario_v2.packages.shared.constants import StatusConfirmacao

_PH = PasswordHasher()


def _agora() -> datetime:
    return datetime.now(UTC)


def _expiracao() -> datetime:
    return _agora() + timedelta(minutes=configuracao_gateway.confirmacao_expiracao_min)


async def criar_confirmacao(
    id_cliente: str, operacao: str, dados_operacao: dict[str, Any]
) -> dict[str, Any]:
    """Cria token de confirmação Step-Up. Retorna {token, url, expira_em}."""
    token = uuid4().hex
    expira = _expiracao().replace(tzinfo=None)

    async with fabrica_sessao() as sessao:
        sessao.add(
            ConfirmacaoPendente(
                token=token,
                id_cliente=id_cliente,
                operacao=operacao,
                dados_operacao_json=json.dumps(dados_operacao, default=str),
                status=StatusConfirmacao.PENDENTE.value,
                expira_em=expira,
            )
        )

    url = f"{configuracao_gateway.gateway_public_url}/confirmar/{token}"
    logger.info("confirmacao_criada", id_cliente=id_cliente, operacao=operacao, token_digest=_redigir_token(token))
    return {"token": token, "url": url, "expira_em": expira.isoformat()}


async def buscar_confirmacao(token: str) -> dict[str, Any] | None:
    async with fabrica_sessao() as sessao:
        res = await sessao.execute(
            select(ConfirmacaoPendente).where(ConfirmacaoPendente.token == token)
        )
        confirmacao = res.scalar_one_or_none()
        if confirmacao is None:
            return None

        cliente = (
            (
                await sessao.execute(
                    select(Cliente).where(Cliente.id_cliente == confirmacao.id_cliente)
                )
            )
            .scalars()
            .first()
        )
        nome = cliente.nome if cliente else "?"

    return {
        "token": confirmacao.token,
        "id_cliente": confirmacao.id_cliente,
        "nome": nome,
        "operacao": confirmacao.operacao,
        "dados_operacao": confirmacao.dados_operacao,
        "status": confirmacao.status,
        "expira_em": confirmacao.expira_em.isoformat(),
        "expirado": confirmacao.expira_em < _agora().replace(tzinfo=None),
        "tentativas_senha": confirmacao.tentativas_senha,
    }


async def validar_e_executar(token: str, senha: str) -> dict[str, Any]:
    """Valida senha + executa a operação real associada ao token."""
    async with fabrica_sessao() as sessao:
        res = await sessao.execute(
            select(ConfirmacaoPendente).where(ConfirmacaoPendente.token == token)
        )
        confirmacao = res.scalar_one_or_none()
        if confirmacao is None:
            return {"sucesso": False, "motivo": "token_invalido"}

        if confirmacao.status != StatusConfirmacao.PENDENTE.value:
            return {"sucesso": False, "motivo": f"status_{confirmacao.status.lower()}"}

        agora = _agora().replace(tzinfo=None)
        if confirmacao.expira_em < agora:
            confirmacao.status = StatusConfirmacao.EXPIRADA.value
            sessao.add(confirmacao)
            return {"sucesso": False, "motivo": "expirado"}

        cliente = (
            await sessao.execute(
                select(Cliente).where(Cliente.id_cliente == confirmacao.id_cliente)
            )
        ).scalar_one_or_none()
        if cliente is None or not cliente.senha_hash:
            return {"sucesso": False, "motivo": "cliente_sem_senha"}

        try:
            _PH.verify(cliente.senha_hash, senha)
        except VerifyMismatchError:
            confirmacao.tentativas_senha += 1
            if confirmacao.tentativas_senha >= configuracao_gateway.confirmacao_max_tentativas:
                confirmacao.status = StatusConfirmacao.REJEITADA.value
                logger.warning("confirmacao_rejeitada_tentativas", token_digest=_redigir_token(token))
            sessao.add(confirmacao)
            tentativas_restantes = max(
                0, configuracao_gateway.confirmacao_max_tentativas - confirmacao.tentativas_senha
            )
            return {
                "sucesso": False,
                "motivo": "senha_incorreta",
                "tentativas_restantes": tentativas_restantes,
            }

        # Executar operação
        operacao = confirmacao.operacao
        dados = confirmacao.dados_operacao
        resultado: dict[str, Any] = {"operacao": operacao}

        if operacao == "aumento_limite":
            from assistente_bancario_v2.banking_gateway.app.db.repositorio import (
                atualizar_limite,
            )

            novo_limite = Decimal(str(dados["novo_limite"]))
            ok = await atualizar_limite(sessao, confirmacao.id_cliente, novo_limite)
            resultado["aplicado"] = ok
            resultado["novo_limite"] = float(novo_limite)
        elif operacao == "criar_transacao":
            from assistente_bancario_v2.banking_gateway.app.services.transacao_service import (
                executar_criacao_transacao,
            )

            tx = await executar_criacao_transacao(
                sessao=sessao, id_cliente=confirmacao.id_cliente, dados=dados
            )
            resultado.update(tx)
        elif operacao == "pagar_conta":
            from assistente_bancario_v2.banking_gateway.app.services.pagamento_service import (
                executar_pagamento_conta,
            )

            pg = await executar_pagamento_conta(
                sessao=sessao, id_cliente=confirmacao.id_cliente, dados=dados
            )
            resultado.update(pg)
        else:
            return {"sucesso": False, "motivo": "operacao_desconhecida"}

        confirmacao.status = StatusConfirmacao.CONFIRMADA.value
        confirmacao.confirmado_em = agora
        sessao.add(confirmacao)
        logger.info("confirmacao_confirmada", token_digest=_redigir_token(token), operacao=operacao)
        return {"sucesso": True, "resultado": resultado}
