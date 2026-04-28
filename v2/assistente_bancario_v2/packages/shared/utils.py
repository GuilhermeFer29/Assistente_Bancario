"""Utilitários compartilhados."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal


def gerar_id_correlacao() -> str:
    """Retorna um id curto para correlacionar logs entre serviços."""
    return uuid.uuid4().hex[:12]


def agora_utc() -> datetime:
    """Retorna o timestamp atual em UTC com timezone."""
    return datetime.now(UTC)


def formatar_brl(valor: float | Decimal | int | str) -> str:
    """Formata um valor numérico em Real Brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "R$ 0,00"
    inteiro, decimal = f"{v:,.2f}".split(".")
    inteiro = inteiro.replace(",", ".")
    return f"R$ {inteiro},{decimal}"


def normalizar_cliente_id(valor: str) -> str:
    """Padroniza id de cliente: tira espaços e converte para maiúsculo."""
    return str(valor).strip().upper()
