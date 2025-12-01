import os
import streamlit as st
import uuid
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

# --- Configuração da Página ---
st.set_page_config(
    page_title="Banco Ágil - Atendimento IA",
    page_icon="🏦",
    layout="centered"
)

# --- Estilos CSS Personalizados ---
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #f0f2f6;
    }
    .assistant-message {
        background-color: #e8f0fe;
        border-left: 5px solid #4a90e2;
    }
</style>
""", unsafe_allow_html=True)

# --- Gerenciamento de Estado (Sessão) ---
# Gera um ID único para o navegador atual se não existir
if "client_id" not in st.session_state:
    st.session_state.client_id = str(uuid.uuid4())

# Inicializa histórico de mensagens e conexão WebSocket
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ws" not in st.session_state:
    st.session_state.ws = None

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bank-building.png", width=80)
    st.title("Painel de Controle")
    st.markdown(f"**ID da Sessão:** `{st.session_state.client_id[:8]}...`")
    
    st.divider()
    
    st.subheader("🛠 Dados para Teste")
    st.markdown("**Cliente 1 (Score 750):**")
    st.code("CPF: 12345678901\nNasc: 1995-02-13", language="text")
    
    st.markdown("**Cliente 2 (Score 680):**")
    st.code("CPF: 98765432100\nNasc: 1996-08-16", language="text")
    
    st.markdown("**Cliente 3 (Score 720):**")
    st.code("CPF: 11122233344\nNasc: 2000-11-07", language="text")
    
    st.divider()
    
    def close_ws_connection():
        ws = st.session_state.get("ws")
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
            finally:
                st.session_state.ws = None

    if st.button("🗑 Limpar Histórico", type="primary"):
        close_ws_connection()
        st.session_state.messages = []
        # Gera novo ID para garantir que o backend "esqueça" o contexto anterior
        st.session_state.client_id = str(uuid.uuid4())
        st.rerun()

    if st.button("🔌 Reconectar WebSocket"):
        close_ws_connection()
        st.experimental_rerun()

# --- Cabeçalho Principal ---
# --- Configuração dinâmica do backend ---
BACKEND_WS_BASE = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/chat/ws").rstrip("/")
STREAM_END_TOKEN = os.getenv("STREAM_END_TOKEN", "__STREAM_END__")

# --- Lógica de Comunicação WebSocket ---
def _ensure_ws_connection(client_id: str):
    uri = f"{BACKEND_WS_BASE}/{client_id}"
    ws = st.session_state.get("ws")
    if ws is not None:
        return ws
    try:
        # Aumentar timeout para dar tempo ao Team Agno inicializar
        ws = connect(uri, open_timeout=15)
        st.session_state.ws = ws
        return ws
    except ConnectionRefusedError:
        return "ERRO: Não foi possível conectar ao servidor. Verifique se o FastAPI está rodando."
    except Exception as exc:
        return f"ERRO: Falha ao abrir o WebSocket ({exc})."


def _receive_stream(ws):
    """Lê os chunks enviados pelo backend até encontrar o token de término."""
    chunks = []
    try:
        while True:
            data = ws.recv()
            if data == STREAM_END_TOKEN:
                break
            if data and data.strip():
                chunks.append(data)
    except Exception as e:
        if chunks:  # Se já recebeu algo, retorna o que tiver
            return chunks
        return [f"ERRO: Falha na comunicação ({e})"]
    return chunks


def send_message_to_agent(message: str, client_id: str):
    """Reaproveita a mesma conexão WebSocket enquanto o usuário estiver na página."""
    ws = _ensure_ws_connection(client_id)
    if isinstance(ws, str):  # mensagem de erro
        return ws

    try:
        ws.send(message)
        return _receive_stream(ws)
    except ConnectionClosed as exc:
        st.session_state.ws = None
        return f"ERRO: Conexão encerrada pelo servidor ({exc}). Clique em 'Reconectar WebSocket' e tente novamente."
    except Exception as exc:
        st.session_state.ws = None
        return f"ERRO: Falha ao usar o WebSocket ({exc})."

# --- Exibição do Histórico de Chat ---
for message in st.session_state.messages:
    role = message["role"]
    avatar = "👤" if role == "user" else "🤖"
    with st.chat_message(role, avatar=avatar):
        st.markdown(message["content"])

# --- Captura de Entrada do Usuário ---
if prompt := st.chat_input("Digite sua mensagem aqui..."):
    # 1. Exibe e guarda mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    # 2. Mostra spinner enquanto aguarda o Agente
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Processando solicitação..."):
            resposta = send_message_to_agent(prompt, st.session_state.client_id)

            if isinstance(resposta, str):
                st.markdown(resposta)
                response_text = resposta
            else:
                response_text = ""
                placeholder = st.empty()
                for chunk in resposta:
                    response_text += chunk
                    placeholder.markdown(response_text)

    # 3. Guarda resposta do assistente
    st.session_state.messages.append({"role": "assistant", "content": response_text})