import streamlit as st
import asyncio
import websockets
import uuid

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

# Inicializa histórico de mensagens
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Barra Lateral (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/bank-building.png", width=80)
    st.title("Painel de Controle")
    st.markdown(f"**ID da Sessão:** `{st.session_state.client_id[:8]}...`")
    
    st.divider()
    
    st.subheader("🛠 Dados para Teste")
    st.markdown("**Cliente 1 (Score Baixo):**")
    st.code("CPF: 12345678900\nNasc: 1990-01-01", language="text")
    
    st.markdown("**Cliente 2 (Score Alto):**")
    st.code("CPF: 11122233344\nNasc: 1985-05-20", language="text")
    
    st.divider()
    
    if st.button("🗑 Limpar Histórico", type="primary"):
        st.session_state.messages = []
        # Gera novo ID para garantir que o backend "esqueça" o contexto anterior
        st.session_state.client_id = str(uuid.uuid4())
        st.rerun()

# --- Cabeçalho Principal ---
st.title("🏦 Banco Ágil")
st.caption("Atendimento Inteligente com Agentes de IA | Powered by Agno & Gemini")

# --- Lógica de Comunicação WebSocket ---
async def send_message_to_agent(message: str, client_id: str):
    """Conecta ao WebSocket do FastAPI, envia msg e aguarda resposta."""
    uri = f"ws://localhost:8000/chat/ws/{client_id}"
    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(message)
            response = await websocket.recv()
            return response
    except ConnectionRefusedError:
        return "ERRO: Não foi possível conectar ao servidor. Verifique se o FastAPI está rodando."
    except Exception as e:
        return f"ERRO: {str(e)}"

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
            # Chama a função async dentro do loop do Streamlit
            response_text = asyncio.run(
                send_message_to_agent(prompt, st.session_state.client_id)
            )
            st.markdown(response_text)
            
    # 3. Guarda resposta do assistente
    st.session_state.messages.append({"role": "assistant", "content": response_text})