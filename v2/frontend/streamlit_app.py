"""Frontend Streamlit do Assistente Bancário V2.

Conecta ao bot_service via WebSocket. Detecta links de Step-Up 2FA
e renderiza UM botão "Abrir confirmação" por link, sem duplicar.
"""

from __future__ import annotations

import os
import re
import uuid
from threading import Thread
from urllib import request as urlrequest
from urllib.parse import urlparse

import streamlit as st
import websocket  # websocket-client

BOT_WS_URL = os.getenv("BOT_WS_URL", "ws://localhost:8000/chat/ws")
GATEWAY_PUBLIC_URL = os.getenv("GATEWAY_PUBLIC_URL", "http://localhost:8001")
STREAM_END_TOKEN = "<<END_OF_STREAM>>"

# URL completa de confirmação (com ou sem markdown wrapper)
REGEX_CONFIRMACAO = re.compile(r"https?://[^\s)\]]+/confirmar/[a-f0-9-]+", re.IGNORECASE)


def _bot_http_base() -> str:
    """Deriva a URL HTTP do bot a partir do BOT_WS_URL (ws→http)."""
    url = urlparse(BOT_WS_URL)
    esquema = "https" if url.scheme == "wss" else "http"
    return f"{esquema}://{url.netloc}"


def _encerrar_sessao_no_bot(session_id: str) -> None:
    try:
        req = urlrequest.Request(
            f"{_bot_http_base()}/chat/encerrar/{session_id}", method="POST"
        )
        urlrequest.urlopen(req, timeout=5).read()  # noqa: S310
    except Exception:  # noqa: BLE001
        pass


# ── Estado de sessão ───────────────────────────────────────────


def _init_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:12]
    if "mensagens" not in st.session_state:
        st.session_state.mensagens = [
            {
                "papel": "assistente",
                "texto": (
                    "👋 Olá! Sou o **Rog**, do Banco Ágil. "
                    "Para começarmos, informe seu **ID de cliente** (ex: `CLI901`)."
                ),
            }
        ]
    if "pergunta_pendente" not in st.session_state:
        st.session_state.pergunta_pendente = None


# ── Comunicação WS (síncrona) ──────────────────────────────────


def _enviar_e_aguardar(texto: str) -> str:
    """Envia uma mensagem ao bot e aguarda resposta completa (token de fim)."""
    url = f"{BOT_WS_URL}/{st.session_state.session_id}"
    resposta_completa: list[str] = []
    erro: list[str] = []

    def _executar() -> None:
        try:
            ws = websocket.WebSocket()
            ws.settimeout(60)
            ws.connect(url)
            ws.send(texto)
            while True:
                msg = ws.recv()
                if msg == STREAM_END_TOKEN:
                    break
                resposta_completa.append(str(msg))
            ws.close()
        except Exception as exc:  # noqa: BLE001
            erro.append(f"Erro de conexão: {exc}")

    thread = Thread(target=_executar)
    thread.start()
    thread.join(timeout=90)

    if erro:
        return erro[0]
    return "".join(resposta_completa) or "(sem resposta do servidor)"


# ── Render do chat ─────────────────────────────────────────────


def _extrair_links_confirmacao(texto: str) -> tuple[str, list[str]]:
    """Extrai URLs de Step-Up do texto e retorna (texto_sem_urls, lista_urls).

    Remove URLs duplicadas (preserva ordem) e remove a linha inteira que continha
    APENAS a URL (com markdown ou sem) para evitar dois botões clicáveis.
    """
    urls = list(dict.fromkeys(REGEX_CONFIRMACAO.findall(texto)))

    texto_limpo = texto
    for url in urls:
        # remove URL e o wrapper markdown [...](url) se houver
        texto_limpo = re.sub(
            rf"\[?[^\[\]\n]*\]?\(?{re.escape(url)}\)?",
            "",
            texto_limpo,
        )
    # Limpa linhas vazias resultantes
    texto_limpo = re.sub(r"\n\s*\n\s*\n+", "\n\n", texto_limpo).strip()
    return texto_limpo, urls


def _renderizar_mensagem(papel: str, texto: str) -> None:
    icone = "🧑" if papel == "usuario" else "🤖"
    role = "user" if papel == "usuario" else "assistant"

    if papel == "usuario":
        with st.chat_message(role, avatar=icone):
            st.markdown(texto)
        return

    texto_limpo, urls = _extrair_links_confirmacao(texto)
    with st.chat_message(role, avatar=icone):
        if texto_limpo:
            st.markdown(texto_limpo)
        for i, url in enumerate(urls, 1):
            rotulo = f"🔒 Abrir confirmação{' #' + str(i) if len(urls) > 1 else ''}"
            st.link_button(rotulo, url=url, use_container_width=True)


# ── App ────────────────────────────────────────────────────────


def main() -> None:
    st.set_page_config(page_title="Banco Ágil V2", page_icon="🏦", layout="centered")
    _init_state()

    with st.sidebar:
        st.markdown("### 🏦 Banco Ágil V2")
        st.caption("Sessão atual:")
        st.code(st.session_state.session_id, language="text")
        if st.button("🔄 Nova conversa", use_container_width=True):
            _encerrar_sessao_no_bot(st.session_state.session_id)
            st.session_state.session_id = uuid.uuid4().hex[:12]
            st.session_state.mensagens = [
                {
                    "papel": "assistente",
                    "texto": "👋 Nova conversa iniciada. Informe seu **ID de cliente**.",
                }
            ]
            st.session_state.pergunta_pendente = None
            st.rerun()
        st.divider()
        st.markdown("**Endpoints**")
        st.markdown(f"- WS: `{BOT_WS_URL}`")
        st.markdown(f"- Gateway: {GATEWAY_PUBLIC_URL}")

    st.title("🏦 Banco Ágil — Assistente V2")
    st.caption("Atendimento bancário com OTP por e-mail e confirmação 2FA.")

    # Renderização única: o loop é a ÚNICA fonte de verdade. A nova mensagem
    # é processada e adicionada ao histórico, depois fazemos rerun.
    for m in st.session_state.mensagens:
        _renderizar_mensagem(m["papel"], m["texto"])

    # Se há pergunta pendente, processa antes de receber input nova
    if st.session_state.pergunta_pendente is not None:
        with st.spinner("🤖 Rog está processando..."):
            resposta = _enviar_e_aguardar(st.session_state.pergunta_pendente)
        st.session_state.mensagens.append({"papel": "assistente", "texto": resposta})
        st.session_state.pergunta_pendente = None
        st.rerun()

    pergunta = st.chat_input("Digite sua mensagem...")
    if pergunta:
        st.session_state.mensagens.append({"papel": "usuario", "texto": pergunta})
        st.session_state.pergunta_pendente = pergunta
        st.rerun()


if __name__ == "__main__":
    main()
