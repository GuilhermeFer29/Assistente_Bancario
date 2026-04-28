"""Constantes compartilhadas entre bot_service e banking_gateway."""

from __future__ import annotations

from enum import Enum


class StatusConta(str, Enum):
    PENDENTE = "PENDENTE"
    PAGA = "PAGA"
    CANCELADA = "CANCELADA"


class TipoConta(str, Enum):
    A_PAGAR = "a_pagar"
    A_RECEBER = "a_receber"


class StatusTransacao(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADA = "CONFIRMADA"
    REJEITADA = "REJEITADA"
    DUPLICADA = "DUPLICADA"


class StatusConfirmacao(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADA = "CONFIRMADA"
    EXPIRADA = "EXPIRADA"
    REJEITADA = "REJEITADA"


class StatusSolicitacaoLimite(str, Enum):
    APROVADO = "aprovado"
    REJEITADO = "rejeitado"


# Token usado pelo bot_service para sinalizar fim de stream WS ao Streamlit
STREAM_END_TOKEN = "<<END_OF_STREAM>>"

# Timezone padrão (Brasil)
TIMEZONE_BR = "America/Sao_Paulo"
