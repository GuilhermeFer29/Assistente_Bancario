"""Modelos SQLModel do banking_gateway."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel

from assistente_bancario_v2.packages.shared.constants import StatusConta


def _agora_utc() -> datetime:
    return datetime.now(UTC)


class Cliente(SQLModel, table=True):
    """Cliente fictício."""

    __tablename__ = "clientes"

    id: int | None = Field(default=None, primary_key=True)
    id_cliente: str = Field(unique=True, index=True)
    nome: str
    email: str = Field(default="")
    telefone: str = Field(default="")
    dt_nascimento: str = Field(default="")  # ISO YYYY-MM-DD
    cpf: str = Field(default="", description="CPF legado V1, não usado em auth")
    score_credito: int = Field(default=0)
    renda_mensal: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    limite_credito: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    confiavel: bool = Field(default=False)
    ativo: bool = Field(default=True)
    senha_hash: str = Field(default="", description="Argon2 hash da senha de transação (Step-Up)")
    criado_em: datetime = Field(default_factory=_agora_utc)


class Saldo(SQLModel, table=True):
    """Saldo bancário."""

    __tablename__ = "saldos"

    id: int | None = Field(default=None, primary_key=True)
    id_cliente: str = Field(unique=True, index=True)
    saldo_disponivel: Decimal = Field(max_digits=12, decimal_places=2)
    saldo_bloqueado: Decimal = Field(default=Decimal("0.00"), max_digits=12, decimal_places=2)
    atualizado_em: datetime = Field(default_factory=_agora_utc)


class Conta(SQLModel, table=True):
    """Conta a pagar ou a receber."""

    __tablename__ = "contas"

    id: int | None = Field(default=None, primary_key=True)
    id_conta: str = Field(unique=True, index=True)
    id_cliente: str = Field(index=True)
    descricao: str
    valor: Decimal = Field(max_digits=12, decimal_places=2)
    data_vencimento: date
    status: str = Field(default=StatusConta.PENDENTE.value)
    tipo: str  # a_pagar | a_receber
    nome_pagador: str | None = Field(default=None)
    data_prevista: date | None = Field(default=None)
    criado_em: datetime = Field(default_factory=_agora_utc)


class Transacao(SQLModel, table=True):
    """Transação criada via Step-Up 2FA."""

    __tablename__ = "transacoes"

    id: int | None = Field(default=None, primary_key=True)
    id_requisicao: str = Field(unique=True, index=True)
    id_cliente: str = Field(index=True)
    chave_idempotencia: str = Field(unique=True, index=True)
    tipo: str
    descricao: str
    valor: Decimal = Field(max_digits=12, decimal_places=2)
    data_vencimento: date
    status: str = Field(default="PENDENTE")
    criado_em: datetime = Field(default_factory=_agora_utc)


class SolicitacaoLimite(SQLModel, table=True):
    """Histórico de solicitações de aumento de limite."""

    __tablename__ = "solicitacoes_limite"

    id: int | None = Field(default=None, primary_key=True)
    id_cliente: str = Field(index=True)
    data_hora_solicitacao: datetime = Field(default_factory=_agora_utc)
    limite_atual: Decimal = Field(max_digits=12, decimal_places=2)
    novo_limite_solicitado: Decimal = Field(max_digits=12, decimal_places=2)
    status_pedido: str  # aprovado | rejeitado


class ScoreCreditoBase(SQLModel, table=True):
    """Tabela de faixas de score → limite máximo permitido."""

    __tablename__ = "score_credito_base"

    id: int | None = Field(default=None, primary_key=True)
    score_min: int
    score_max: int
    limite_maximo: Decimal = Field(max_digits=12, decimal_places=2)


class Otp(SQLModel, table=True):
    """OTP para autenticação por e-mail."""

    __tablename__ = "otps"

    id: int | None = Field(default=None, primary_key=True)
    id_cliente: str = Field(index=True)
    codigo_hash: str = Field(description="Argon2 do código OTP (6 dígitos)")
    criado_em: datetime = Field(default_factory=_agora_utc)
    expira_em: datetime
    tentativas: int = Field(default=0)
    consumido: bool = Field(default=False)
    bloqueado_ate: datetime | None = Field(default=None)


class ConfirmacaoPendente(SQLModel, table=True):
    """Token de confirmação Step-Up 2FA."""

    __tablename__ = "confirmacoes_pendentes"

    id: int | None = Field(default=None, primary_key=True)
    token: str = Field(unique=True, index=True)
    id_cliente: str = Field(index=True)
    operacao: str = Field(description="aumento_limite | criar_transacao")
    dados_operacao_json: str = Field(description="JSON serializado da operação")
    status: str = Field(default="PENDENTE")
    tentativas_senha: int = Field(default=0)
    criado_em: datetime = Field(default_factory=_agora_utc)
    expira_em: datetime
    confirmado_em: datetime | None = Field(default=None)

    @property
    def dados_operacao(self) -> dict:  # type: ignore[type-arg]
        """Deserializa o JSON de dados da operação."""
        return json.loads(self.dados_operacao_json)
