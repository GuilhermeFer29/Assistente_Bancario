"""Testa serialização do HttpGatewayClient — Decimal/date/datetime."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from assistente_bancario_v2.bot_service.app.services.gateway_client import (
    _normalizar_payload,
)


def test_normaliza_decimal() -> None:
    assert _normalizar_payload(Decimal("1234.56")) == "1234.56"


def test_normaliza_date() -> None:
    assert _normalizar_payload(date(2026, 4, 28)) == "2026-04-28"


def test_normaliza_datetime() -> None:
    assert _normalizar_payload(datetime(2026, 4, 28, 12, 0)) == "2026-04-28T12:00:00"


def test_normaliza_dict_aninhado() -> None:
    payload = {
        "valor": Decimal("100.50"),
        "data": date(2026, 4, 28),
        "items": [Decimal("10"), {"sub": Decimal("20")}],
        "texto": "ok",
        "num": 5,
    }
    out = _normalizar_payload(payload)
    assert out == {
        "valor": "100.50",
        "data": "2026-04-28",
        "items": ["10", {"sub": "20"}],
        "texto": "ok",
        "num": 5,
    }


def test_passa_tipos_basicos_intactos() -> None:
    assert _normalizar_payload("texto") == "texto"
    assert _normalizar_payload(42) == 42
    assert _normalizar_payload(3.14) == 3.14
    assert _normalizar_payload(True) is True
    assert _normalizar_payload(None) is None
