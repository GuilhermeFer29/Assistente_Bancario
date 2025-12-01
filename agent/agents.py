import re
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.tavily import TavilyTools
from agno.db.sqlite import SqliteDb
from dotenv import load_dotenv
from tools import tools
from typing import Dict, Tuple

MAX_AUTH_ATTEMPTS = 3

load_dotenv()

model = Gemini(id="gemini-2.5-flash-lite", temperature=0.3)
db = SqliteDb(db_file="data/agno_sessions.db")

# Dicionário para armazenar o estado de autenticação por sessão
session_states: Dict[str, Dict] = {}


def _get_session_state(session_id: str) -> Dict:
    """Garante que cada sessão tenha um dicionário inicial padrão."""
    if session_id not in session_states:
        session_states[session_id] = {
            'erros': 0,
            'bloqueado': False,
            'authenticated': False,
            'cpf': None,
            'dt_nascimento': None,
            'nome_cliente': "Cliente",
            'score_credito': None,
            'ultimo_limite': None,
            'last_agent': None,
        }
    return session_states[session_id]


def _format_team_response(run_response, stream_enabled: bool) -> Tuple[bool, object]:
    if stream_enabled:
        return True, run_response
    return False, str(run_response.content)


def get_auth_tool_for_session(session_id: str):
    """Feramenta de validação de cliente com controle de tentativas por sessão."""
    _get_session_state(session_id)

    def validar_cliente_com_seguranca(cpf: str, data_nascimento: str) -> str:
        state = _get_session_state(session_id)

        if state['bloqueado'] or state['erros'] >= 3:
            return "SISTEMA: Acesso BLOQUEADO por excesso de tentativas. O atendimento deve ser encerrado imediatamente."

        try:
            resultado = tools.validando_cliente(cpf, data_nascimento)
        except AttributeError:
            return "Erro técnico: Função de validação não encontrada no tools.py"
        except Exception as exc:  # salvaguarda
            return f"Erro ao validar cliente: {exc}"

        # Compatibilidade com retornos legados em string
        if not isinstance(resultado, dict):
            texto = str(resultado)
            if any(palavra in texto for palavra in ["FALHA", "Erro", "não", "Não"]):
                state['erros'] += 1
                tentativas_restantes = 3 - state['erros']
                if state['erros'] >= 3:
                    state['bloqueado'] = True
                    return "FALHA FINAL: Você excedeu o número máximo de 3 tentativas. O sistema bloqueou o acesso. Encerre o atendimento."
                return f"FALHA: Dados incorretos. Você tem mais {tentativas_restantes} tentativas."

            state['cpf'] = cpf
            state['dt_nascimento'] = data_nascimento
            state['authenticated'] = True
            state['erros'] = 0
            state['bloqueado'] = False
            state['nome_cliente'] = state.get('nome_cliente') or "Cliente"
            return texto

        status = resultado.get('status')
        mensagem = resultado.get('mensagem', 'Autenticação processada.')

        if status != 'ok':
            state['erros'] += 1
            tentativas_restantes = max(0, 3 - state['erros'])
            if state['erros'] >= MAX_AUTH_ATTEMPTS:
                state['bloqueado'] = True
                return (
                    mensagem
                    + " O acesso foi bloqueado após três tentativas. Encerre o atendimento."
                )
            return f"{mensagem} Você ainda possui {tentativas_restantes} tentativa(s)."

        state['cpf'] = cpf
        state['dt_nascimento'] = data_nascimento
        state['authenticated'] = True
        state['erros'] = 0
        state['bloqueado'] = False
        state['nome_cliente'] = resultado.get('nome', 'Cliente') or 'Cliente'
        state['score_credito'] = resultado.get('score_credito')

        return mensagem

    return validar_cliente_com_seguranca

def criar_agente_coordenador(session_id: str) -> Agent:
    ferramenta_validacao_segura = get_auth_tool_for_session(session_id)
    
    # Especialista em câmbio - seguindo pattern Agno
    cambio_search_agent = Agent(
        name="CurrencyExchangeAgent",
        role="Especialista em câmbio fornecendo cotações em tempo real e análise de mercado",
        tools=[TavilyTools()],
        instructions=[
            "Você é um especialista em câmbio do Banco Ágil.",
            "Sempre pesquise cotações atuais usando suas ferramentas.",
            "Forneça informações claras e concisas sobre valores de moedas e datas.",
            "Sugira serviços relacionados quando apropriado.",
            "Formate respostas em markdown para melhor legibilidade."
        ],
        model=model,
        markdown=True,
    )

    # Especialista em entrevista de crédito - seguindo pattern Agno
    entrevistador_credito_agent = Agent(
        name="CreditInterviewAgent", 
        role="Especialista em avaliação de crédito conduzindo entrevistas financeiras e pontuação",
        tools=[tools.atualizar_score_cliente],
        instructions=[
            "Você é um especialista em avaliação de crédito do Banco Ágil.",
            "Conduza entrevistas financeiras estruturadas cobrindo: renda, despesas, emprego, dependentes e dívidas.",
            "Use dados do cliente do contexto quando disponível para evitar perguntas redundantes.",
            "Só chame a ferramenta de atualização de score após coletar todas as informações necessárias.",
            "Após atualizações de score, explique claramente o novo score e próximos passos.",
            "Mantenha tom profissional mas conversacional durante todo o processo."
        ],
        model=model,
        markdown=True,
    )

    # Especialista em crédito - seguindo pattern Agno
    analise_credito_agent = Agent(
        name="CreditManagementAgent",
        role="Gestor de limites de crédito tratando consultas e solicitações de aumento",
        tools=[
            tools.validando_cliente,
            tools.consultando_limite,
            tools.solicitacao_de_limite,
        ],
        instructions=[
            "Você é um gestor de crédito do Banco Ágil.",
            "CONTEXTO: Cliente já está autenticado. Use CPF/Data do contexto para ferramentas.",
            "",
            "FLUXO CONVERSACIONAL:",
            "1. Para consultas de limite: consulte e informe valor atual",
            "2. Para aumentos: informe limite atual, explique regras de score, pergunte se deseja prosseguir",
            "3. Se cliente confirmar (sim/quero/confirmar): processe solicitação IMEDIATAMENTE",
            "4. Retorne resultado (aprovado/rejeitado) com próximos passos",
            "",
            "IMPORTANTE:",
            "- Mantenha tom conversacional e profissional",
            "- Use dados do contexto sem pedir novamente",
            "- Não repita informações já fornecidas",
            "- Se cliente disser 'sim' após pergunta de confirmação, processe sem mais perguntas"
        ],
        model=model,
        markdown=True,
    )

    # Adicionar contador para evitar loops
    def _check_delegation_loop(session_id: str, max_delegations: int = 3) -> bool:
        """Verifica se há loop de delegação na sessão."""
        state = _get_session_state(session_id)
        delegation_count = state.get('delegation_count', 0)
        if delegation_count >= max_delegations:
            return True  # Loop detectado
        state['delegation_count'] = delegation_count + 1
        return False

    # Funções delegadas otimizadas
    def delegar_para_cambio(solicitacao: str) -> str:
        """Delega solicitações de câmbio para especialista."""
        # Verificar loop antes de delegar
        if _check_delegation_loop(session_id):
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente."
        
        print(f"🔍 COORDENADOR: Delegando para agente de câmbio: {solicitacao}")
        state = _get_session_state(session_id)
        # Compartilhar estado de autenticação com especialista
        specialist_session = f"{session_id}-cambio"
        if state.get('cpf') and state.get('dt_nascimento'):
            # Copiar estado de autenticação para sessão do especialista
            session_states[specialist_session] = state.copy()
        context = ""
        if state.get('cpf') and state.get('dt_nascimento'):
            context = f"CONTEXTO DO CLIENTE: Cliente autenticado - CPF: {state['cpf']}, Data Nasc: {state['dt_nascimento']}. "
        response = cambio_search_agent.run(context + solicitacao, session_id=specialist_session, stream=False)
        return str(response.content)

    def delegar_para_entrevista(solicitacao: str) -> str:
        """Delega solicitações de entrevista para especialista."""
        # Verificar loop antes de delegar
        if _check_delegation_loop(session_id):
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente."
        
        print(f"🔍 COORDENADOR: Delegando para agente de entrevista: {solicitacao}")
        state = _get_session_state(session_id)
        # Compartilhar estado de autenticação com especialista
        specialist_session = f"{session_id}-interview"
        if state.get('cpf') and state.get('dt_nascimento'):
            # Copiar estado de autenticação para sessão do especialista
            session_states[specialist_session] = state.copy()
        context = ""
        if state.get('cpf') and state.get('dt_nascimento'):
            context = f"CONTEXTO DO CLIENTE: Cliente autenticado - CPF: {state['cpf']}, Data Nasc: {state['dt_nascimento']}. Use estes dados para ferramentas, não peça novamente. "
        response = entrevistador_credito_agent.run(context + solicitacao, session_id=specialist_session, stream=False)
        return str(response.content)

    def delegar_para_credito(solicitacao: str) -> str:
        """Delega solicitações de crédito para especialista."""
        # Verificar loop antes de delegar
        if _check_delegation_loop(session_id):
            return "Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente."
        
        print(f"🔍 COORDENADOR: Delegando para agente de crédito: {solicitacao}")
        state = _get_session_state(session_id)
        # Compartilhar estado de autenticação com especialista
        specialist_session = f"{session_id}-credit"
        if state.get('cpf') and state.get('dt_nascimento'):
            # Copiar estado de autenticação para sessão do especialista
            session_states[specialist_session] = state.copy()
        context = ""
        if state.get('cpf') and state.get('dt_nascimento'):
            context = f"CONTEXTO DO CLIENTE: Cliente autenticado - CPF: {state['cpf']}, Data Nasc: {state['dt_nascimento']}. Use estes dados para ferramentas, não peça novamente. "
        response = analise_credito_agent.run(context + solicitacao, session_id=specialist_session, stream=False)
        return str(response.content)

    # Coordenador principal - seguindo pattern Agno
    coordenador = Agent(
        name="BankingCoordinatorAgent",
        role="Coordenador bancário principal gerenciando solicitações de clientes e delegação de especialistas",
        description="Você é o coordenador principal dos serviços bancários do Banco Ágil. Analisa solicitações de clientes e delega para especialistas apropriados mantendo conversação contínua.",
        tools=[
            ferramenta_validacao_segura,
            delegar_para_cambio,
            delegar_para_entrevista,
            delegar_para_credito,
        ],
        instructions=[
            "Você é o coordenador principal do Banco Ágil, responsável pelo atendimento contínuo ao cliente.",
            "",
            "SAUDAÇÃO INICIAL:",
            "- Se é a primeira mensagem do cliente (histórico vazio), responda: 'Bem-vindo ao Banco Ágil! Para acessar nossos serviços, preciso autenticar você. Por favor, informe seu CPF e data de nascimento (formato: DD/MM/AAAA).'",
            "- SEMPRE comece com 'Banco Ágil' na saudação",
            "",
            "AUTENTICAÇÃO:",
            "- Se cliente não está autenticado, SEMPRE peça CPF e data de nascimento primeiro",
            "- Quando cliente fornecer CPF e data → CHAME IMEDIATAMENTE validar_cliente_com_seguranca",
            "- Após autenticação bem-sucedida → Responda: '✅ Bem-vindo ao Banco Ágil, [nome]! Autenticação confirmada. Como posso ajudar você hoje?'",
            "",
            "CONTEXTO CONVERSACIONAL:",
            "- Mantenha o histórico de conversa em mente",
            "- Se cliente já foi autenticado, NÃO peça CPF novamente",
            "- Reconheça quando cliente está continuando uma conversa anterior",
            "- Se cliente disser 'oi' após já estar autenticado, responda: 'Olá! Bem-vindo de volta ao Banco Ágil. Como posso ajudar?'",
            "",
            "REGRAS DE DELEGAÇÃO (IMEDIATAS):",
            "- Se cliente disser 'limite', 'crédito', 'aumentar', 'consultar' → CHAME IMEDIATAMENTE delegar_para_credito",
            "- Se cliente disser 'câmbio', 'dólar', 'euro', 'cotação' → CHAME IMEDIATAMENTE delegar_para_cambio", 
            "- Se cliente disser 'entrevista', 'score', 'renda', 'emprego' → CHAME IMEDIATAMENTE delegar_para_entrevista",
            "",
            "IMPORTANTE:",
            "- NUNCA pergunte 'o que você precisa' se cliente já pediu algo específico",
            "- SEMPRE chame a ferramenta específica para solicitações de crédito/câmbio/entrevista",
            "- Mantenha conversação natural e contínua",
            "- Sempre mencione 'Banco Ágil' nas saudações",
            "",
            "CRÍTICO: SEMPRE use uma ferramenta para solicitações específicas. NUNCA responda diretamente sobre crédito/câmbio!"
        ],
        model=model,
        markdown=True,
        db=db,
        num_history_messages=10,
        add_history_to_context=True,
        read_chat_history=True,
        store_history_messages=True,
    )

    return coordenador

agent_sessions: Dict[str, Agent] = {}


def get_agent(session_id: str) -> Agent:
    if session_id not in agent_sessions:
        agent_sessions[session_id] = criar_agente_coordenador(session_id)
    return agent_sessions[session_id]


def limpar_sessoes_team(session_id: str):
    if session_id in agent_sessions:
        del agent_sessions[session_id]
        if session_id in session_states:
            del session_states[session_id]


def processar_mensagem(session_id: str, mensagem: str, stream: bool = False) -> Tuple[bool, object]:
    """Processa mensagem usando agente coordenador do Agno."""
    # Resetar contador de delegação a cada nova mensagem
    state = _get_session_state(session_id)
    state['delegation_count'] = 0
    
    print(f"🚀 PROCESSANDO: session_id={session_id}, mensagem='{mensagem}', stream={stream}")
    agent = get_agent(session_id)
    
    try:
        print(f"📞 CHAMANDO AGENTE COM STREAM={stream}")
        resposta = agent.run(mensagem, stream=stream, session_id=session_id)
        print(f"✅ RESPOSTA RECEBIDA: {type(resposta)}")
        return _format_team_response(resposta, stream)
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        # Em caso de erro, tentar sem streaming
        if stream:
            print("🔄 TENTANDO SEM STREAM...")
            resposta = agent.run(mensagem, stream=False, session_id=session_id)
            return _format_team_response(resposta, False)
        raise e