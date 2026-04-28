"""Testa a extração/limpeza de URLs de Step-Up no frontend Streamlit."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "frontend"))

# Import direto da função (sem rodar Streamlit)
from streamlit_app import _extrair_links_confirmacao  # noqa: E402


def test_extrai_url_simples() -> None:
    texto = "Abra o link: http://localhost:8001/confirmar/abc123def"
    limpo, urls = _extrair_links_confirmacao(texto)
    assert urls == ["http://localhost:8001/confirmar/abc123def"]
    assert "/confirmar/" not in limpo


def test_extrai_url_em_markdown() -> None:
    texto = "Para confirmar [clique aqui](http://localhost:8001/confirmar/abc789def)"
    limpo, urls = _extrair_links_confirmacao(texto)
    assert urls == ["http://localhost:8001/confirmar/abc789def"]
    assert "clique aqui" not in limpo
    assert "(" not in limpo or limpo.count("(") == limpo.count(")")


def test_remove_duplicatas() -> None:
    texto = (
        "Aqui: http://localhost:8001/confirmar/aaa\n"
        "E também: http://localhost:8001/confirmar/aaa"
    )
    _, urls = _extrair_links_confirmacao(texto)
    assert urls == ["http://localhost:8001/confirmar/aaa"]


def test_extrai_multiplas_urls_distintas() -> None:
    texto = (
        "Conta 1: http://localhost:8001/confirmar/aaa\n"
        "Conta 2: http://localhost:8001/confirmar/bbb\n"
        "Conta 3: http://localhost:8001/confirmar/ccc"
    )
    _, urls = _extrair_links_confirmacao(texto)
    assert len(urls) == 3
    assert all("/confirmar/" in u for u in urls)


def test_preserva_texto_que_nao_e_url() -> None:
    texto = "Olá! Tudo bem? Sem links aqui."
    limpo, urls = _extrair_links_confirmacao(texto)
    assert urls == []
    assert "Olá! Tudo bem?" in limpo


def test_url_com_uuid_hex_com_traco() -> None:
    texto = "Link: http://gateway:8001/confirmar/abc123-def456-789"
    _, urls = _extrair_links_confirmacao(texto)
    assert urls == ["http://gateway:8001/confirmar/abc123-def456-789"]


def test_remove_linhas_vazias_apos_limpeza() -> None:
    texto = (
        "Confirme:\n\n"
        "http://localhost:8001/confirmar/aaa\n\n"
        "Obrigado."
    )
    limpo, urls = _extrair_links_confirmacao(texto)
    assert len(urls) == 1
    # Não deve ter 3+ quebras seguidas
    assert "\n\n\n" not in limpo
