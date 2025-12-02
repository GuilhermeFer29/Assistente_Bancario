"""
Frontend Streamlit do Banco Ágil
Interface minimalista com tema bancário (azul e preto)
"""
import os
import streamlit as st
import uuid
from websockets.sync.client import connect
from websockets.exceptions import ConnectionClosed

# --- Configuração da Página ---
st.set_page_config(
    page_title="Banco Ágil",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Tema Minimalista Azul/Preto ---
st.markdown("""
<style>
    /* Reset e esconder elementos Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Fundo principal */
    .stApp {
        background: linear-gradient(180deg, #0a0a0f 0%, #0d1117 100%);
    }
    
    /* Container principal */
    .main .block-container {
        padding: 1rem 1rem 6rem 1rem;
        max-width: 700px;
    }
    
    /* Header do banco */
    .bank-header {
        text-align: center;
        padding: 2rem 0;
        border-bottom: 1px solid #1e3a5f;
        margin-bottom: 1.5rem;
    }
    
    .bank-logo {
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 1rem auto;
        font-size: 1.8rem;
    }
    
    .bank-name {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: 0.5px;
        margin: 0;
    }
    
    .bank-tagline {
        font-size: 0.75rem;
        color: #64748b;
        margin-top: 0.25rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    
    .session-id {
        font-size: 0.65rem;
        color: #475569;
        margin-top: 0.75rem;
        font-family: 'Courier New', monospace;
    }
    
    .session-id span {
        color: #3b82f6;
    }
    
    /* Container de mensagens */
    .stChatMessage {
        background: transparent !important;
        border: none !important;
    }
    
    /* Mensagem do usuário */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #1e293b !important;
        border-radius: 12px;
        margin: 0.5rem 0;
        border-left: 3px solid #3b82f6 !important;
    }
    
    /* Mensagem do assistente */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: #0f172a !important;
        border-radius: 12px;
        margin: 0.5rem 0;
        border-left: 3px solid #1e3a5f !important;
    }
    
    /* Texto das mensagens */
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] span {
        color: #e2e8f0 !important;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    
    /* Input de chat */
    [data-testid="stChatInput"] {
        background: #0f172a !important;
        border: 1px solid #1e3a5f !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stChatInput"] textarea {
        color: #e2e8f0 !important;
        background: transparent !important;
    }
    
    [data-testid="stChatInput"] textarea::placeholder {
        color: #475569 !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0a0a0f !important;
        border-right: 1px solid #1e3a5f;
    }
    
    [data-testid="stSidebar"] * {
        color: #94a3b8 !important;
    }
    
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #e2e8f0 !important;
        font-size: 0.85rem !important;
    }
    
    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        font-size: 0.75rem !important;
        padding: 0.4rem 0.8rem !important;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: #1e293b !important;
        border-radius: 6px !important;
        font-size: 0.8rem !important;
    }
    
    /* Divider */
    hr {
        border-color: #1e3a5f !important;
        opacity: 0.5;
    }
    
    /* Code blocks */
    code {
        background: #1e293b !important;
        color: #3b82f6 !important;
        font-size: 0.75rem !important;
        padding: 0.1rem 0.3rem !important;
        border-radius: 3px !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #3b82f6 transparent transparent transparent !important;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 4px;
        height: 4px;
    }
    ::-webkit-scrollbar-track {
        background: #0a0a0f;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e3a5f;
        border-radius: 2px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #2563eb;
    }
</style>
""", unsafe_allow_html=True)

# --- Configurações ---
BACKEND_WS_BASE = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/chat/ws").rstrip("/")
STREAM_END_TOKEN = os.getenv("STREAM_END_TOKEN", "__STREAM_END__")

WELCOME_MESSAGE = """Bem-vindo ao **Banco Ágil**! 🏦

Digite **Iniciar** para começar o atendimento.

---

**Clientes para teste:**

| Nome | CPF | Nascimento |
|------|-----|------------|
| Guilherme | `12345678901` | `13/02/1995` |
| Leci | `98765432100` | `16/08/1996` |
| Safira | `11122233344` | `07/11/2000` |

---

*Digite **Finalizar** a qualquer momento para encerrar.*"""

SESSION_START_INFO = """✅ **Sessão iniciada!** Aguarde a resposta do atendente..."""

END_MESSAGE = """Atendimento encerrado. Obrigado por utilizar o **Banco Ágil**! 🏦

Digite **Iniciar** para um novo atendimento."""


# --- Estado da Sessão ---
def init_session():
    defaults = {
        "client_id": str(uuid.uuid4()),
        "messages": [],
        "ws": None,
        "connected": False,
        "welcome_sent": False,
        "session_active": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def close_connection():
    """Fecha a conexão WebSocket."""
    if st.session_state.get("ws"):
        try:
            st.session_state.ws.close()
        except:
            pass
    st.session_state.ws = None
    st.session_state.connected = False


def end_session():
    """Finaliza a sessão atual e prepara para nova."""
    close_connection()
    st.session_state.session_active = False


def start_new_session():
    """Inicia uma nova sessão com novo ID."""
    close_connection()
    st.session_state.client_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.ws = None
    st.session_state.connected = False
    st.session_state.welcome_sent = False
    st.session_state.session_active = True


def reset_all():
    """Reset completo."""
    close_connection()
    st.session_state.messages = []
    st.session_state.client_id = str(uuid.uuid4())
    st.session_state.ws = None
    st.session_state.connected = False
    st.session_state.welcome_sent = False
    st.session_state.session_active = False


# --- WebSocket ---
def get_connection(client_id: str):
    if st.session_state.ws:
        return st.session_state.ws
    
    try:
        ws = connect(f"{BACKEND_WS_BASE}/{client_id}", open_timeout=15)
        st.session_state.ws = ws
        st.session_state.connected = True
        return ws
    except:
        st.session_state.connected = False
        return None


def send_message(message: str, client_id: str) -> str:
    ws = get_connection(client_id)
    
    if not ws:
        return "Não foi possível conectar ao servidor."
    
    try:
        ws.send(message)
        chunks = []
        while True:
            data = ws.recv()
            if data == STREAM_END_TOKEN:
                break
            if data and data.strip():
                chunks.append(data)
        return "".join(chunks) if chunks else "Sem resposta do servidor."
    except ConnectionClosed:
        st.session_state.ws = None
        st.session_state.connected = False
        return "Conexão perdida. Tente novamente."
    except Exception as e:
        st.session_state.ws = None
        st.session_state.connected = False
        return f"Erro: {str(e)}"


# --- Inicialização ---
init_session()

# --- Header ---
st.markdown(f"""
<div class="bank-header">
    <div class="bank-logo">🏦</div>
    <h1 class="bank-name">Banco Ágil</h1>
    <p class="bank-tagline">Atendimento Inteligente 24h</p>
    <p class="session-id">Sessão: <span>{st.session_state.client_id[:8]}...</span></p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### Controles")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Limpar"):
            reset_all()
            st.rerun()
    with col2:
        if st.button("🔌 Reconectar"):
            close_connection()
            st.rerun()
    
    st.divider()
    
    # Status
    status = "🟢 Ativo" if st.session_state.session_active else "⚪ Aguardando"
    st.markdown(f"**Status:** {status}")
    
    st.divider()
    
    st.markdown("### Clientes Teste")
    
    with st.expander("Guilherme"):
        st.code("12345678901\n13/02/1995")
    
    with st.expander("Leci"):
        st.code("98765432100\n16/08/1996")
    
    with st.expander("Safira"):
        st.code("11122233344\n07/11/2000")

# --- Mensagem de Boas-Vindas ---
if not st.session_state.welcome_sent and not st.session_state.messages:
    st.session_state.messages.append({"role": "assistant", "content": WELCOME_MESSAGE})
    st.session_state.welcome_sent = True

# --- Histórico ---
for msg in st.session_state.messages:
    avatar = "👤" if msg["role"] == "user" else "🏦"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# --- Input ---
if prompt := st.chat_input("Digite sua mensagem..."):
    # Detectar comando INICIAR
    if prompt.strip().lower() in ["iniciar", "inicio", "começar", "start"]:
        # Adicionar mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Iniciar nova sessão (gera novo client_id, limpa conexão)
        close_connection()
        st.session_state.client_id = str(uuid.uuid4())
        st.session_state.session_active = True
        
        # Adicionar dados de teste ao histórico PRIMEIRO
        st.session_state.messages.append({"role": "assistant", "content": SESSION_START_INFO})
        
        # Conectar e enviar "Iniciar" para o agente
        response = send_message("Iniciar", st.session_state.client_id)
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()
    
    # Detectar comando FINALIZAR
    elif prompt.strip().lower() in ["finalizar", "encerrar", "sair", "fim", "exit"]:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Encerrar sessão
        end_session()
        
        st.session_state.messages.append({"role": "assistant", "content": END_MESSAGE})
        st.rerun()
    
    # Mensagem normal
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Se sessão não está ativa, pedir para iniciar
        if not st.session_state.session_active:
            response = "Por favor, digite **Iniciar** para começar o atendimento."
            st.session_state.messages.append({"role": "assistant", "content": response})
        else:
            with st.chat_message("user", avatar="👤"):
                st.markdown(prompt)
            
            with st.chat_message("assistant", avatar="🏦"):
                with st.spinner(""):
                    response = send_message(prompt, st.session_state.client_id)
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.rerun()
