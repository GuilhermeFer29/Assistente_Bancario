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
        
        # Armazena credenciais validadas na sessão
        state['cpf'] = cpf
        state['dt_nascimento'] = data_nascimento
        state['authenticated'] = True
        
        return resultado

    return validar_cliente_com_seguranca

def criar_agente_triagem(session_id: str) -> Agent:
    ferramenta_validacao_segura = get_auth_tool_for_session(session_id)

    # --- Definição dos Agentes Especialistas dentro do escopo da sessão ---
    # Isso permite que eles compartilhem ferramentas de navegação se necessário,
    # mas principalmente, permite que o Triagem orquestre melhor.

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
            "ATENÇÃO: Verifique se o CPF e Data de Nascimento já foram fornecidos no contexto da mensagem.",
            "Se os dados do cliente (CPF, Data de Nascimento) já estiverem no contexto, NÃO PERGUNTE NOVAMENTE. Use-os para registrar a solicitação no final.",
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
            "ATENÇÃO: Verifique se o CPF e Data de Nascimento já foram fornecidos no contexto da mensagem.",
            "Se SIM (já tem CPF e Data): Use-os IMEDIATAMENTE para chamar a ferramenta `validando_cliente` e `consultando_limite`. NÃO PERGUNTE NOVAMENTE.",
            "Se NÃO: Pergunte ao usuário.",
            "Primeiro, valide o cliente usando a ferramenta `validando_cliente`.",
            "Se o cliente for válido, consulte o limite atual com `consultando_limite`.",
            "Se o cliente desejar aumentar o limite, NÃO diga apenas para ele procurar o entrevistador. INFORME ao Agente de Triagem que a entrevista é necessária.",
            "Após a entrevista (se o cliente mencionar que já fez), utilize `solicitacao_de_limite`.",
            "Forneça respostas claras e objetivas, focando nas necessidades do cliente.",
            "Finalize o atendimento de forma cordial."
        ],
        model=model,
        markdown=True
    )

    def chamar_agente_cambio(solicitacao: str) -> str:
        """Aciona o especialista em câmbio para cotações."""
        response = cambio_search_agent.run(solicitacao, session_id=session_id)
        return str(response.content)

    def chamar_agente_entrevista(solicitacao: str) -> str:
        """Aciona o especialista em entrevista para atualizar cadastro/score."""
        state = session_states.get(session_id, {})
        cpf = state.get('cpf')
        dt_nascimento = state.get('dt_nascimento')
        
        # Marca que estamos em uma entrevista
        state['last_agent'] = 'entrevista'
        
        contexto_extra = ""
        if cpf and dt_nascimento:
            contexto_extra = f"SISTEMA: O cliente JÁ ESTÁ AUTENTICADO. Dados: CPF='{cpf}', Data de Nascimento='{dt_nascimento}'. Use estes dados para as ferramentas e NÃO pergunte novamente. "
        
        # Adiciona instrução explícita para iniciar a entrevista se a solicitação for vaga
        instrucao_inicio = " INICIE A ENTREVISTA IMEDIATAMENTE PERGUNTANDO A RENDA MENSAL."
        
        response = entrevistador_credito_agent.run(contexto_extra + solicitacao + instrucao_inicio, session_id=session_id)
        resp_str = str(response.content)
        
        # Se a entrevista terminou (score atualizado), limpa o estado
        if "novo score" in resp_str.lower() or "voltar ao agente de crédito" in resp_str.lower():
             state['last_agent'] = None
             
        return resp_str

    def chamar_agente_credito(solicitacao: str) -> str:
        """Aciona o especialista em crédito para limites e validações."""
        state = session_states.get(session_id, {})
        cpf = state.get('cpf')
        dt_nascimento = state.get('dt_nascimento')
        
        contexto_extra = ""
        if cpf and dt_nascimento:
            contexto_extra = f"SISTEMA: O cliente JÁ ESTÁ AUTENTICADO. Dados: CPF='{cpf}', Data de Nascimento='{dt_nascimento}'. Use estes dados para as ferramentas e NÃO pergunte novamente. "

        response = analise_credito_agent.run(contexto_extra + solicitacao, session_id=session_id)
        return str(response.content)

    def instrucoes_dinamicas(agent) -> str:
        state = session_states.get(session_id, {})
        authenticated = state.get('authenticated', False)
        cpf = state.get('cpf', 'N/A')
        last_agent = state.get('last_agent')
        
        base_instructions = """
        Você é o primeiro contato do Banco Ágil. Siga este fluxo ESTRITAMENTE:
        """
        
        if authenticated:
            instructions = base_instructions + f"""
            STATUS ATUAL: O CLIENTE JÁ ESTÁ AUTENTICADO (CPF: {cpf}).
            """
            
            if last_agent == 'entrevista':
                instructions += """
                ATENÇÃO: O usuário está no meio de uma entrevista com o Agente de Entrevista.
                QUALQUER resposta do usuário (números, 'sim', 'não', valores) deve ser encaminhada IMEDIATAMENTE para a ferramenta `chamar_agente_entrevista`.
                NÃO tente interpretar a resposta. Apenas repasse para o especialista.
                """
            else:
                instructions += """
                --- FASE 2: DIRECIONAMENTO (IMEDIATO) ---
                1. NÃO peça CPF ou Data de Nascimento novamente. O cliente já foi validado.
                2. Identifique a intenção do usuário.
                3. Delegue para o membro correto da sua equipe usando as ferramentas disponíveis:
                   - 'Quero ver meu limite' -> Use `chamar_agente_credito`.
                   - 'Aumentar limite' ou 'Solicitar aumento' -> ATENÇÃO: Isso requer duas etapas.
                     PRIMEIRO: Use `chamar_agente_entrevista` para atualizar os dados.
                     SEGUNDO: Se a entrevista for bem sucedida, use `chamar_agente_credito` para efetivar o aumento.
                   - 'Atualizar cadastro' ou 'Melhorar score' -> Use `chamar_agente_entrevista`.
                   - 'Cotação de moeda' -> Use `chamar_agente_cambio`.
                4. Não tente resolver problemas de crédito ou câmbio sozinho. Use as ferramentas de delegação.
                """
            return instructions
        else:
            return base_instructions + """
            STATUS ATUAL: CLIENTE NÃO AUTENTICADO.
            
            --- FASE 1: AUTENTICAÇÃO ---
            1. Solicite CPF e Data de Nascimento.
            2. Use a ferramenta `validar_cliente_com_seguranca` para conferir os dados.
            3. Se a ferramenta retornar 'FALHA' (e tentativas restantes), peça os dados novamente.
            4. CRÍTICO: Se a ferramenta retornar 'FALHA FINAL' ou 'BLOQUEADO', encerre o atendimento imediatamente.
            
            APÓS SUCESSO NA AUTENTICAÇÃO, prossiga para a Fase 2 (Direcionamento).
            """

    return Agent(
        name="Agente de Triagem",
        role="Recepcionista e Coordenador de Atendimento ao Cliente",
        tools=[
            ferramenta_validacao_segura,
            chamar_agente_cambio,
            chamar_agente_entrevista,
            chamar_agente_credito
        ], 
        instructions=instrucoes_dinamicas,
        model=model,
        markdown=True,
        debug_mode=True,
        add_history_to_context=True, 
        num_history_messages=10
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