"""
Entry Point para Streamlit Community Cloud
Inicia FastAPI em background thread e serve o frontend Streamlit.
"""
import os
import sys
import time
import threading
import streamlit as st

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def get_api_keys_from_secrets():
    """Tenta obter API keys do st.secrets (Streamlit Cloud) ou session_state."""
    google_key = None
    tavily_key = None
    
    # Tentar st.secrets primeiro (Streamlit Cloud)
    try:
        google_key = st.secrets.get("GOOGLE_API_KEY")
        tavily_key = st.secrets.get("TAVILY_API_KEY")
    except:
        pass
    
    # Fallback para session_state (configurado pelo usuário)
    if not google_key and "GOOGLE_API_KEY" in st.session_state:
        google_key = st.session_state.GOOGLE_API_KEY
    if not tavily_key and "TAVILY_API_KEY" in st.session_state:
        tavily_key = st.session_state.TAVILY_API_KEY
    
    # Fallback para variáveis de ambiente
    if not google_key:
        google_key = os.getenv("GOOGLE_API_KEY")
    if not tavily_key:
        tavily_key = os.getenv("TAVILY_API_KEY")
    
    return google_key, tavily_key


def set_api_keys_in_env(google_key: str, tavily_key: str = None):
    """Define as API keys nas variáveis de ambiente."""
    if google_key:
        os.environ["GOOGLE_API_KEY"] = google_key
    if tavily_key:
        os.environ["TAVILY_API_KEY"] = tavily_key


def is_port_in_use(port: int) -> bool:
    """Verifica se a porta já está em uso."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return False
        except OSError:
            return True


def start_fastapi_server():
    """Inicia o servidor FastAPI em uma thread separada."""
    import uvicorn
    from main import app
    
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    
    # Verificar se a porta já está em uso
    if is_port_in_use(port):
        print(f"⚠️ Porta {port} já está em uso. FastAPI provavelmente já está rodando.")
        return
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False
    )


def ensure_fastapi_running():
    """Garante que o FastAPI está rodando em background."""
    if "fastapi_started" not in st.session_state:
        st.session_state.fastapi_started = False
    
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    
    # Se a porta já está em uso, assumir que FastAPI está rodando
    if is_port_in_use(port):
        st.session_state.fastapi_started = True
        return
    
    if not st.session_state.fastapi_started:
        # Iniciar FastAPI em thread daemon
        fastapi_thread = threading.Thread(target=start_fastapi_server, daemon=True)
        fastapi_thread.start()
        st.session_state.fastapi_started = True
        
        # Aguardar servidor iniciar
        time.sleep(2)


def show_api_config_page():
    """Mostra a página de configuração de API keys."""
    st.set_page_config(
        page_title="Banco Ágil - Configuração",
        page_icon="🔐",
        layout="centered"
    )
    
    # CSS para tema escuro
    st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(180deg, #0a0a0f 0%, #0d1117 100%);
        }
        .config-header {
            text-align: center;
            padding: 2rem 0;
            color: white;
        }
        .config-header h1 {
            color: #3b82f6;
            font-size: 2rem;
        }
        .config-header p {
            color: #94a3b8;
        }
        .stTextInput > label {
            color: #e2e8f0 !important;
        }
        .stTextInput input {
            background: #1e293b !important;
            color: #e2e8f0 !important;
            border: 1px solid #1e3a5f !important;
        }
        .stButton > button {
            background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%) !important;
            color: white !important;
            border: none !important;
            width: 100%;
            padding: 0.75rem !important;
            font-size: 1rem !important;
        }
        .info-box {
            background: #1e293b;
            border: 1px solid #1e3a5f;
            border-radius: 8px;
            padding: 1rem;
            margin: 1rem 0;
            color: #94a3b8;
            font-size: 0.85rem;
        }
        .info-box a {
            color: #3b82f6;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="config-header">
        <h1>🏦 Banco Ágil</h1>
        <p>Configure suas chaves de API para começar</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Formulário de API Keys
    with st.form("api_keys_form"):
        st.markdown("### 🔑 Chaves de API")
        
        google_key = st.text_input(
            "Google Gemini API Key *",
            type="password",
            placeholder="AIza...",
            help="Obrigatória para o funcionamento do assistente"
        )
        
        st.markdown("""
        <div class="info-box">
            📌 <strong>Obtenha sua chave:</strong> 
            <a href="https://aistudio.google.com/apikey" target="_blank">Google AI Studio</a>
            <br>Crie uma conta Google e gere sua API key gratuitamente.
        </div>
        """, unsafe_allow_html=True)
        
        tavily_key = st.text_input(
            "Tavily API Key (opcional)",
            type="password",
            placeholder="tvly-...",
            help="Necessária apenas para consultas de câmbio em tempo real"
        )
        
        st.markdown("""
        <div class="info-box">
            💱 <strong>Para cotações de câmbio:</strong>
            <a href="https://app.tavily.com/home" target="_blank">Tavily</a>
            <br>Opcional - sem ela, a função de câmbio não funcionará.
        </div>
        """, unsafe_allow_html=True)
        
        submitted = st.form_submit_button("🚀 Iniciar Assistente", use_container_width=True)
        
        if submitted:
            if not google_key:
                st.error("❌ A chave da Google Gemini é obrigatória!")
            else:
                # Salvar no session_state
                st.session_state.GOOGLE_API_KEY = google_key
                if tavily_key:
                    st.session_state.TAVILY_API_KEY = tavily_key
                
                # Definir nas variáveis de ambiente
                set_api_keys_in_env(google_key, tavily_key)
                
                st.session_state.api_configured = True
                st.success("✅ Chaves configuradas com sucesso!")
                time.sleep(1)
                st.rerun()
    
    st.markdown("---")
    
    with st.expander("ℹ️ Sobre o Banco Ágil"):
        st.markdown("""
        O **Banco Ágil** é um assistente bancário virtual demonstrativo que oferece:
        
        - 🔐 **Autenticação** via CPF e data de nascimento
        - 💳 **Consulta e aumento de limite** de crédito
        - 📋 **Entrevista de crédito** para atualização de score
        - 💱 **Cotações de câmbio** em tempo real
        
        **Clientes de Teste:**
        | Nome | CPF | Nascimento |
        |------|-----|------------|
        | Guilherme | `12345678901` | `13/02/1995` |
        | Leci | `98765432100` | `16/08/1996` |
        | Safira | `11122233344` | `07/11/2000` |
        """)


def run_main_app():
    """Executa o aplicativo principal do frontend."""
    # Importar e executar o frontend original
    import importlib.util
    spec = importlib.util.spec_from_file_location("streamlit_front", "frontend/streamlit_front.py")
    frontend_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frontend_module)


def main():
    """Função principal que gerencia o fluxo do app."""
    # Verificar se já tem API keys configuradas
    google_key, tavily_key = get_api_keys_from_secrets()
    
    # Se já tem keys (via secrets ou env), configurar e prosseguir
    if google_key:
        set_api_keys_in_env(google_key, tavily_key)
        st.session_state.api_configured = True
    
    # Verificar se precisa mostrar tela de configuração
    if not st.session_state.get("api_configured", False):
        show_api_config_page()
        return
    
    # Garantir que FastAPI está rodando
    ensure_fastapi_running()
    
    # Executar o app principal
    run_main_app()


if __name__ == "__main__":
    main()
