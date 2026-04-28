"""Seed do banco a partir dos CSVs V1 (idempotente)."""

from __future__ import annotations

import csv
import random
import secrets
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from assistente_bancario_v2.banking_gateway.app.core.logging_config import logger
from assistente_bancario_v2.banking_gateway.app.db.models import (
    Cliente,
    Conta,
    Saldo,
    ScoreCreditoBase,
)
from assistente_bancario_v2.packages.shared.constants import StatusConta, TipoConta

# Resolve sempre relativo à raiz do projeto v2/, independente do CWD do processo.
# `__file__` está em v2/assistente_bancario_v2/banking_gateway/app/db/seed.py.
# parents[0]=db, [1]=app, [2]=banking_gateway, [3]=assistente_bancario_v2, [4]=v2.
_PROJETO_RAIZ = Path(__file__).resolve().parents[4]
_DATA_SEED = _PROJETO_RAIZ / "data" / "seed"
_PH = PasswordHasher()

_SENHA_TX_PADRAO = "1234"  # senha de transação dev


def _slug(nome: str) -> str:
    return (
        "".join(c for c in nome.strip().lower() if c.isalnum() or c == " ")
        .replace(" ", ".")
    )


def _id_cliente_de_cpf(cpf: str) -> str:
    return f"CLI{cpf[-3:]}"


async def _seed_score_base(sessao: AsyncSession, csv_path: Path) -> int:
    res = await sessao.execute(select(ScoreCreditoBase))
    if res.scalars().first():
        return 0
    inseridos = 0
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sessao.add(
                ScoreCreditoBase(
                    score_min=int(row["score_min"]),
                    score_max=int(row["score_max"]),
                    limite_maximo=Decimal(row["limite_maximo"]),
                )
            )
            inseridos += 1
    await sessao.flush()
    return inseridos


async def _seed_clientes(sessao: AsyncSession, csv_path: Path) -> int:
    inseridos = 0
    senha_hash = _PH.hash(_SENHA_TX_PADRAO)
    with csv_path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cpf = row["cpf"].strip()
            id_cliente = _id_cliente_de_cpf(cpf)
            res = await sessao.execute(
                select(Cliente).where(Cliente.id_cliente == id_cliente)
            )
            if res.scalar_one_or_none():
                continue
            nome = row["nome"].strip()
            sessao.add(
                Cliente(
                    id_cliente=id_cliente,
                    nome=nome,
                    email=f"{_slug(nome)}@bancoagil.local",
                    telefone="",
                    dt_nascimento=row["dt_nascimento"].strip(),
                    cpf=cpf,
                    score_credito=int(float(row["score_credito"])),
                    renda_mensal=Decimal(row["renda_mensal"]),
                    limite_credito=Decimal(row["limite_credito"]),
                    confiavel=True,
                    ativo=True,
                    senha_hash=senha_hash,
                )
            )
            inseridos += 1
    await sessao.flush()
    return inseridos


async def _seed_saldos_e_contas(sessao: AsyncSession) -> tuple[int, int]:
    rng = random.Random(42)
    saldos_inseridos = 0
    contas_inseridas = 0

    res = await sessao.execute(select(Cliente))
    clientes = list(res.scalars().all())
    for cliente in clientes:
        res_saldo = await sessao.execute(
            select(Saldo).where(Saldo.id_cliente == cliente.id_cliente)
        )
        if res_saldo.scalar_one_or_none():
            continue

        saldo_disp = Decimal(str(round(rng.uniform(5_000, 10_000), 2)))
        sessao.add(Saldo(id_cliente=cliente.id_cliente, saldo_disponivel=saldo_disp))
        saldos_inseridos += 1

        hoje = date.today()
        for i in range(3):
            sessao.add(
                Conta(
                    id_conta=uuid4().hex[:10],
                    id_cliente=cliente.id_cliente,
                    descricao=f"Conta a pagar #{i + 1}",
                    valor=Decimal(str(round(rng.uniform(50, 800), 2))),
                    data_vencimento=hoje + timedelta(days=rng.randint(-15, 60)),
                    status=StatusConta.PENDENTE.value,
                    tipo=TipoConta.A_PAGAR.value,
                )
            )
            contas_inseridas += 1
        for i in range(3):
            sessao.add(
                Conta(
                    id_conta=uuid4().hex[:10],
                    id_cliente=cliente.id_cliente,
                    descricao=f"Recebimento #{i + 1}",
                    valor=Decimal(str(round(rng.uniform(100, 1500), 2))),
                    data_vencimento=hoje + timedelta(days=rng.randint(-5, 45)),
                    status=StatusConta.PENDENTE.value,
                    tipo=TipoConta.A_RECEBER.value,
                    nome_pagador=f"Pagador {secrets.token_hex(2)}",
                )
            )
            contas_inseridas += 1

    await sessao.flush()
    return saldos_inseridos, contas_inseridas


async def executar_seed(sessao: AsyncSession) -> None:
    """Executa o seed do banco (idempotente)."""
    clientes_csv = _DATA_SEED / "clientes.csv"
    score_csv = _DATA_SEED / "score_credito_base.csv"

    if not clientes_csv.exists() or not score_csv.exists():
        logger.warning(
            "seed_csv_nao_encontrado", clientes=str(clientes_csv), score=str(score_csv)
        )
        return

    score_inseridos = await _seed_score_base(sessao, score_csv)
    clientes_inseridos = await _seed_clientes(sessao, clientes_csv)
    saldos_inseridos, contas_inseridas = await _seed_saldos_e_contas(sessao)

    logger.info(
        "seed_concluido",
        score=score_inseridos,
        clientes=clientes_inseridos,
        saldos=saldos_inseridos,
        contas=contas_inseridas,
    )
