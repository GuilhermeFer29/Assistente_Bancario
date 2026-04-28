"""Testes do módulo packages/shared/utils.py."""

from __future__ import annotations

from datetime import datetime, timezone

from assistente_bancario_v2.packages.shared.utils import (
    agora_utc,
    formatar_brl,
    gerar_id_correlacao,
    normalizar_cliente_id,
)


def test_gerar_id_correlacao_tem_12_chars() -> None:
    cid = gerar_id_correlacao()
    assert len(cid) == 12
    assert isinstance(cid, str)


def test_gerar_id_correlacao_eh_unico() -> None:
    assert gerar_id_correlacao() != gerar_id_correlacao()


def test_agora_utc_tem_timezone() -> None:
    agora = agora_utc()
    assert isinstance(agora, datetime)
    assert agora.tzinfo == timezone.utc


def test_formatar_brl_inteiro() -> None:
    assert formatar_brl(1234) == "R$ 1.234,00"


def test_formatar_brl_decimais() -> None:
    assert formatar_brl(1234.5) == "R$ 1.234,50"


def test_formatar_brl_grande() -> None:
    assert formatar_brl(1234567.89) == "R$ 1.234.567,89"


def test_formatar_brl_invalido_devolve_zero() -> None:
    assert formatar_brl("abc") == "R$ 0,00"


def test_normalizar_cliente_id_remove_espacos() -> None:
    assert normalizar_cliente_id("  cli001  ") == "CLI001"


def test_normalizar_cliente_id_uppercase() -> None:
    assert normalizar_cliente_id("cli001") == "CLI001"
