"""Schemas Pydantic do banking_gateway."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Cliente ──────────────────────────────────────────────────────


class RespostaCliente(BaseModel):
    id_cliente: str
    nome: str
    email: str
    telefone: str
    confiavel: bool
    ativo: bool


class RespostaEmailCliente(BaseModel):
    id_cliente: str
    email: str


# ── Saldo ────────────────────────────────────────────────────────


class RespostaSaldo(BaseModel):
    id_cliente: str
    nome: str
    saldo_disponivel: Decimal
    saldo_bloqueado: Decimal
    moeda: str = "BRL"
    atualizado_em: datetime


# ── Contas ───────────────────────────────────────────────────────


class RespostaConta(BaseModel):
    id_conta: str
    id_cliente: str
    descricao: str
    valor: Decimal
    data_vencimento: date
    status: str
    tipo: str
    nome_pagador: str | None = None
    data_prevista: date | None = None


class RespostaListaContas(BaseModel):
    contas: list[RespostaConta]
    total: int
    total_valor: Decimal


# ── Crédito / Score ──────────────────────────────────────────────


class RespostaLimite(BaseModel):
    id_cliente: str
    nome: str
    limite_atual: Decimal
    score: int


class RequisicaoAumentoLimite(BaseModel):
    id_cliente: str
    novo_limite: Decimal = Field(..., gt=0)


class RespostaAumentoLimite(BaseModel):
    """Resposta da solicitação de aumento.

    Em V2, quando exige Step-Up, retornamos `requer_confirmacao=True` + `url_confirmacao`.
    Em fluxo direto (sem step-up), retorna `aprovado` ou `rejeitado` com motivo.
    """

    aprovado: bool
    requer_confirmacao: bool = False
    url_confirmacao: str | None = None
    token_confirmacao: str | None = None
    novo_limite: Decimal | None = None
    limite_maximo_permitido: Decimal | None = None
    mensagem: str = ""


class RequisicaoAtualizarScore(BaseModel):
    id_cliente: str
    renda: Decimal = Field(..., ge=0)
    tipo_emprego: str
    despesas_mensais: Decimal = Field(..., ge=0)
    dependentes: int = Field(..., ge=0)
    tem_dividas: str  # "sim" | "nao"


class RespostaAtualizarScore(BaseModel):
    sucesso: bool
    novo_score: int | None = None
    mensagem: str = ""


# ── Transação ────────────────────────────────────────────────────


class RequisicaoTransacao(BaseModel):
    id_cliente: str
    tipo: str = Field(..., pattern="^(a_pagar|a_receber)$")
    descricao: str = Field(..., min_length=3, max_length=200)
    valor: Decimal = Field(..., gt=0)
    data_vencimento: date
    nome_pagador: str | None = None
    data_prevista: date | None = None
    chave_idempotencia: str | None = None


class RespostaTransacao(BaseModel):
    id_requisicao: str
    status: str
    mensagem: str
    criado_em: datetime
    requer_confirmacao: bool = False
    url_confirmacao: str | None = None
    token_confirmacao: str | None = None


# ── OTP ──────────────────────────────────────────────────────────


class RequisicaoOtpIniciar(BaseModel):
    id_cliente: str


class RespostaOtpIniciar(BaseModel):
    enviado: bool
    expira_em: datetime | None = None
    mensagem: str = ""


class RequisicaoOtpValidar(BaseModel):
    id_cliente: str
    codigo: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class RespostaOtpValidar(BaseModel):
    valido: bool
    motivo: str | None = None
    nome: str | None = None


# ── Confirmação Step-Up ──────────────────────────────────────────


class RequisicaoCriarConfirmacao(BaseModel):
    id_cliente: str
    operacao: str  # aumento_limite | criar_transacao
    dados_operacao: dict  # type: ignore[type-arg]


class RespostaCriarConfirmacao(BaseModel):
    token: str
    url: str
    expira_em: datetime
