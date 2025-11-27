from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.tavily import TavilyTools
from dotenv import load_dotenv
from tools import tools 
from typing import Dict

load_dotenv()

model = Gemini(id="gemini-2.5-flash", temperature=0.3)
# Dicionário para armazenar o estado de autenticação por sessão
session_states: Dict[str, Dict] = {}

def get_auth_tool_for_session(session_id: str):
    """Feramenta de validação de cliente com controle de tentativas por sessão."""
    if session_id not in session_states:
        session_states[session_id] = {'erros': 0, 'bloqueado': False}

    def validar_cliente_com_seguranca(cpf: str, data_nascimento: str) -> str:
        state = session_states[session_id]

        if state['bloqueado'] or state['erros'] >= 3:
            return "SISTEMA: Acesso BLOQUEADO por excesso de tentativas. O atendimento deve ser encerrado imediatamente."

        try:
            resultado = tools.validando_cliente(cpf, data_nascimento) 
        except AttributeError:
            return "Erro técnico: Função de validação não encontrada no tools.py"

        if "FALHA" in resultado or "Erro" in resultado or "Não" in resultado:
            state['erros'] += 1
            tentativas_restantes = 3 - state['erros']
            
            if state['erros'] >= 3:
                state['bloqueado'] = True
                return "FALHA FINAL: Você excedeu o número máximo de 3 tentativas. O sistema bloqueou o acesso. Encerre o atendimento."
            
            return f"FALHA: Dados incorretos. Você tem mais {tentativas_restantes} tentativas."
        
        return resultado

    return validar_cliente_com_seguranca

cambio_search_agent = Agent(
    name = "Agente de Câmbio",
    role="Especialista em Analise de moedas estrangeiras e mercado cambial.",
    tools=[TavilyTools()],
    instructions=[
        "Você é um agente especializado em análise de câmbio e mercado financeiro.",
        "Utilize a ferramenta 'TavilyTools' disponíveis para consultar cotações ATUAL de moeda solicitada.",
        "Seja claro e objetivo em suas respostas e evite jargões técnicos.",
        "Seja direto : Informe o valor ea data da cotação",
        "Responda de forma clara e concisa, focando nas necessidades do usuário.",
        "Após Informar a Coração, encerre seu atendimento cordialmente."
    ],
    model=model,
    markdown=True
)

entrevistador_credito_agent = Agent(
    name = "Agente de Entrevista de Crédito",
    role="Especialista em análise de crédito e avaliação financeira.",
    tools=[tools.atualizar_score_cliente],
    instructions=[
        "Seu objetivo é entrevistar o cliente para recalcular seu score financeiro.",
        "Você DEVE coletar as seguintes informações obrigatoriamente:",
        "1. Renda mensal (número positivo).",
        "2. Despesas mensais (número positivo).",
        "3. Tipo de emprego (apenas: 'formal', 'autônomo' ou 'desempregado'), caso venha outro nome classifique para um desses.",
        "4. Número de dependentes (0 ou mais).",
        "5. Existência de dívidas ativas ('sim' ou 'não').",
        "Não tente adivinhar valores. Pergunte ao usuário um por um se necessário.",
        "Somente quando tiver TODAS as informações, chame a ferramenta `atualizar_score_cliente`.",
        "Após atualizar, informe o novo score e sugira voltar ao Agente de Crédito."
    ],
    model=model,
    markdown=True
)

analise_credito_agent = Agent(
    name = "Agente de Crédito",
    role="Gestor de limites de Crédito",
    tools=[
        tools.validando_cliente,
        tools.consultando_limite,
        tools.solicitacao_de_limite,
    ],
    instructions=[
        "Seu objetivo é gerenciar limites de crédito para clientes bancários.",
        "Primeiro, valide o cliente usando a ferramenta `validando_cliente`.",
        "Se o cliente for válido, consulte o limite atual com `consultando_limite`.",
        "Se o cliente desejar aumentar o limite, oriente-o a passar pela entrevista com o Agente de Entrevista de Crédito.",
        "Após a entrevista, se o cliente quiser solicitar um aumento, utilize `solicitacao_de_limite`.",
        "Forneça respostas claras e objetivas, focando nas necessidades do cliente.",
        "Finalize o atendimento de forma cordial."
    ],
    model=model,
    markdown=True
)

# Criação do Agente de Triagem com autenticação segura
def criar_agente_triagem(session_id: str) -> Agent:
    ferramenta_validacao_segura = get_auth_tool_for_session(session_id)

    def chamar_agente_cambio(solicitacao: str) -> str:
        """Aciona o especialista em câmbio para cotações."""
        response = cambio_search_agent.run(solicitacao, session_id=session_id)
        return str(response.content)

    def chamar_agente_entrevista(solicitacao: str) -> str:
        """Aciona o especialista em entrevista para atualizar cadastro/score."""
        response = entrevistador_credito_agent.run(solicitacao, session_id=session_id)
        return str(response.content)

    def chamar_agente_credito(solicitacao: str) -> str:
        """Aciona o especialista em crédito para limites e validações."""
        response = analise_credito_agent.run(solicitacao, session_id=session_id)
        return str(response.content)

    return Agent(
        name="Agente de Triagem",
        role="Recepcionista e Coordenador de Atendimento ao Cliente",
        tools=[
            ferramenta_validacao_segura,
            chamar_agente_cambio,
            chamar_agente_entrevista,
            chamar_agente_credito
        ], 
        instructions=[
            "Você é o primeiro contato do Banco Ágil. Siga este fluxo ESTRITAMENTE:",
            "--- FASE 1: AUTENTICAÇÃO ---",
            "1. Verifique no histórico se o cliente já foi autenticado (se já temos o nome e CPF confirmados).",
            "2. Se NÃO autenticado: Solicite CPF e Data de Nascimento.",
            "3. Use a ferramenta `validar_cliente_com_seguranca` para conferir os dados.",
            "4. Se a ferramenta retornar 'FALHA' (e tentativas restantes), peça os dados novamente.",
            "5. CRÍTICO: Se a ferramenta retornar 'FALHA FINAL' ou 'BLOQUEADO', encerre o atendimento imediatamente e não aceite mais inputs.",
            "--- FASE 2: DIRECIONAMENTO ---",
            "6. APENAS SE AUTENTICADO COM SUCESSO: Pergunte ou identifique como pode ajudar.",
            "7. Com base na intenção, delegue para o membro correto da sua equipe usando as ferramentas disponíveis:",
            "   - 'Quero ver meu limite' ou 'Aumentar limite' -> Use `chamar_agente_credito`.",
            "   - 'Atualizar cadastro' ou 'Melhorar score' -> Use `chamar_agente_entrevista`.",
            "   - 'Cotação de moeda' -> Use `chamar_agente_cambio`.",
            "Não tente resolver problemas de crédito ou câmbio sozinho. Use as ferramentas de delegação."
        ],
        model=model,
        markdown=True,
        debug_mode=True
    )

agent_sessions : Dict[str, Agent] = {}

def secao_agente(session_id: str) -> Agent:
    if session_id not in agent_sessions:
        agent_sessions[session_id] = criar_agente_triagem(session_id)
    return agent_sessions[session_id]

def limpar_sessoes_agentes(session_id: str):
    if session_id in agent_sessions:
        del agent_sessions[session_id]
        if session_id in session_states:
            del session_states[session_id]