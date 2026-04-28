"""Funções de acesso ao banco (repositório).

Mantemos puras operações sobre AsyncSession. Tanto rotas HTTP
(`api/*.py`) quanto o transporte in_process (`bot_service`) consomem
estas funções.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.db.models import (
    Cliente,
    Conta,
    Saldo,
    ScoreCreditoBase,
)
from assistente_bancario_v2.packages.shared.constants import StatusConta

# ── Cliente ──────────────────────────────────────────────────


async def buscar_cliente(sessao: AsyncSession, id_cliente: str) -> Cliente | None:
    res = await sessao.execute(select(Cliente).where(Cliente.id_cliente == id_cliente))
    return res.scalar_one_or_none()


# ── Saldo ────────────────────────────────────────────────────


async def buscar_saldo(sessao: AsyncSession, id_cliente: str) -> Saldo | None:
    res = await sessao.execute(select(Saldo).where(Saldo.id_cliente == id_cliente))
    return res.scalar_one_or_none()


# ── Contas ───────────────────────────────────────────────────


def _hoje() -> date:
    return date.today()


async def listar_contas(
    sessao: AsyncSession,
    *,
    id_cliente: str,
    tipo: str,  # a_vencer | vencidas | pagas
    data_inicio: date | None = None,
    data_fim: date | None = None,
) -> list[Conta]:
    stmt = select(Conta).where(Conta.id_cliente == id_cliente)

    hoje = _hoje()
    if tipo == "a_vencer":
        stmt = stmt.where(
            Conta.status == StatusConta.PENDENTE.value,
            Conta.data_vencimento >= hoje,
        )
    elif tipo == "vencidas":
        stmt = stmt.where(
            Conta.status == StatusConta.PENDENTE.value,
            Conta.data_vencimento < hoje,
        )
    elif tipo == "pagas":
        stmt = stmt.where(Conta.status == StatusConta.PAGA.value)

    if data_inicio:
        stmt = stmt.where(Conta.data_vencimento >= data_inicio)
    if data_fim:
        stmt = stmt.where(Conta.data_vencimento <= data_fim)

    res = await sessao.execute(stmt)
    return list(res.scalars().all())


# ── Score / Limite ───────────────────────────────────────────


async def faixa_de_score(
    sessao: AsyncSession, score: int
) -> ScoreCreditoBase | None:
    res = await sessao.execute(
        select(ScoreCreditoBase).where(
            ScoreCreditoBase.score_min <= score, ScoreCreditoBase.score_max >= score
        )
    )
    return res.scalar_one_or_none()


async def atualizar_limite(
    sessao: AsyncSession, id_cliente: str, novo_limite: Decimal
) -> bool:
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        return False
    cliente.limite_credito = novo_limite
    sessao.add(cliente)
    await sessao.flush()
    return True


async def atualizar_score(
    sessao: AsyncSession, id_cliente: str, novo_score: int
) -> bool:
    cliente = await buscar_cliente(sessao, id_cliente)
    if cliente is None:
        return False
    cliente.score_credito = novo_score
    sessao.add(cliente)
    await sessao.flush()
    return True
