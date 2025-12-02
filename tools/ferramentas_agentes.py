"""
Ferramentas para os Agentes do Banco Ágil
Cada função retorna uma ferramenta vinculada à sessão do cliente.
"""
from typing import Dict
from tools import tools

MAX_AUTH_ATTEMPTS = 3

# Estado de autenticação por sessão (em memória)
session_states: Dict[str, Dict] = {}


def get_session_state(session_id: str) -> Dict:
    """Retorna ou inicializa o estado da sessão."""
    if session_id not in session_states:
        session_states[session_id] = {
            "tentativas_auth": 0,
            "bloqueado": False,
            "autenticado": False,
            "cpf": None,
            "nome": None,
            "score_credito": None,
            "limite_atual": None,
            # Campos para persistir dados parciais de autenticação
            "cpf_pendente": None,
            "data_nascimento_pendente": None,
        }
    return session_states[session_id]


def limpar_estado_sessao(session_id: str) -> None:
    """Remove o estado da sessão."""
    if session_id in session_states:
        del session_states[session_id]

# FERRAMENTAS DE TRIAGEM (AUTENTICAÇÃO)

def criar_ferramenta_registrar_cpf(session_id: str):
    """
    Cria ferramenta para registrar CPF na sessão.
    Usada quando cliente informa apenas o CPF.
    """
    
    def registrar_cpf(cpf: str) -> str:
        """
        Registra o CPF do cliente na sessão atual.
        
        Use quando o cliente informar APENAS o CPF (sem data de nascimento).
        O CPF ficará salvo na sessão até que a data de nascimento seja informada.
        
        Args:
            cpf: CPF do cliente com 11 dígitos (ex: 12345678901).
        
        Returns:
            Confirmação de que o CPF foi registrado e orientação para pedir a data.
        """
        state = get_session_state(session_id)
        
        if state["bloqueado"]:
            return "STATUS: BLOQUEADO. Acesso bloqueado por segurança."
        
        if state["autenticado"]:
            return f"STATUS: JA_AUTENTICADO. Cliente {state['nome']} já identificado."
        
        # Limpar formatação do CPF
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        state["cpf_pendente"] = cpf_limpo
        
        # Verificar se já tem data pendente para autenticar
        if state["data_nascimento_pendente"]:
            # Temos ambos os dados, autenticar!
            resultado = tools.validando_cliente(cpf_limpo, state["data_nascimento_pendente"])
            if resultado["status"] == "ok":
                state["autenticado"] = True
                state["cpf"] = cpf_limpo
                state["nome"] = resultado.get("nome", "Cliente")
                state["score_credito"] = resultado.get("score_credito")
                state["cpf_pendente"] = None
                state["data_nascimento_pendente"] = None
                return f"STATUS: SUCESSO. Cliente {state['nome']} autenticado. Score: {state['score_credito']}. Perguntar como pode ajudar."
        
        return "STATUS: CPF_REGISTRADO. CPF salvo. Solicitar data de nascimento no formato DD/MM/AAAA."
    
    return registrar_cpf

def criar_ferramenta_registrar_data_nascimento(session_id: str):
    """
    Cria ferramenta para registrar data de nascimento e tentar autenticação.
    Usada quando cliente informa a data de nascimento.
    """
    
    def registrar_data_nascimento(data_nascimento: str) -> str:
        """
        Registra a data de nascimento e tenta autenticar se já tiver CPF.
        
        Use quando o cliente informar a data de nascimento.
        Se o CPF já foi registrado anteriormente, a autenticação será feita automaticamente.
        
        Args:
            data_nascimento: Data de nascimento no formato DD/MM/AAAA (ex: 13/02/1995).
        
        Returns:
            - Se CPF já está registrado: resultado da autenticação
            - Se CPF não está registrado: pede o CPF
        """
        state = get_session_state(session_id)
        
        if state["bloqueado"]:
            return "STATUS: BLOQUEADO. Acesso bloqueado por segurança."
        
        if state["autenticado"]:
            return f"STATUS: JA_AUTENTICADO. Cliente {state['nome']} já identificado."
        
        state["data_nascimento_pendente"] = data_nascimento
        
        # Verificar se já tem CPF pendente para autenticar
        if state["cpf_pendente"]:
            # Temos ambos os dados, autenticar!
            resultado = tools.validando_cliente(state["cpf_pendente"], data_nascimento)
            
            if resultado["status"] == "ok":
                state["autenticado"] = True
                state["cpf"] = state["cpf_pendente"]
                state["nome"] = resultado.get("nome", "Cliente")
                state["score_credito"] = resultado.get("score_credito")
                state["cpf_pendente"] = None
                state["data_nascimento_pendente"] = None
                return f"STATUS: SUCESSO. Cliente {state['nome']} autenticado. Score: {state['score_credito']}. Perguntar como pode ajudar."
            
            # Falha na autenticação
            state["tentativas_auth"] += 1
            tentativas_restantes = MAX_AUTH_ATTEMPTS - state["tentativas_auth"]
            
            # Limpar dados pendentes para nova tentativa
            state["cpf_pendente"] = None
            state["data_nascimento_pendente"] = None
            
            if tentativas_restantes <= 0:
                state["bloqueado"] = True
                return "STATUS: BLOQUEADO. Tentativas esgotadas. Orientar cliente a contatar Central 0800-123-4567."
            
            return f"STATUS: DADOS_INVALIDOS. Tentativas restantes: {tentativas_restantes}. Solicitar novamente CPF e data de nascimento."
        
        return "STATUS: DATA_REGISTRADA. Data salva. Solicitar CPF com 11 dígitos."
    
    return registrar_data_nascimento

def criar_ferramenta_autenticacao(session_id: str):
    """
    Cria ferramenta de autenticação com controle de tentativas por sessão.
    Usada pelo Agente de Triagem.
    """
    
    def autenticar_cliente(cpf: str, data_nascimento: str) -> str:
        """
        Autentica o cliente usando CPF e data de nascimento.
        
        Esta ferramenta valida as credenciais do cliente no sistema.
        Permite até 3 tentativas antes de bloquear o acesso por segurança.
        
        Args:
            cpf: CPF do cliente com 11 dígitos. Pode ser com ou sem formatação (ex: 12345678901 ou 123.456.789-01).
            data_nascimento: Data de nascimento do cliente. Aceita formato DD/MM/AAAA ou AAAA-MM-DD.
        
        Returns:
            String com o status da autenticação:
            - SUCESSO: Cliente autenticado com nome e score
            - DADOS_INVALIDOS: Dados não conferem, mostra tentativas restantes
            - BLOQUEADO: Acesso bloqueado, orientar contato com central
            - JA_AUTENTICADO: Cliente já está autenticado na sessão
        """
        state = get_session_state(session_id)
        
        if state["bloqueado"]:
            return "STATUS: BLOQUEADO. Acesso bloqueado por segurança. Orientar cliente a contatar Central 0800-123-4567."
        
        if state["autenticado"]:
            return f"STATUS: JA_AUTENTICADO. Cliente {state['nome']} já identificado."
        
        resultado = tools.validando_cliente(cpf, data_nascimento)
        
        if resultado["status"] == "ok":
            state["autenticado"] = True
            state["cpf"] = cpf
            state["nome"] = resultado.get("nome", "Cliente")
            state["score_credito"] = resultado.get("score_credito")
            state["tentativas_auth"] = 0
            return f"STATUS: SUCESSO. Cliente {state['nome']} autenticado. Score: {state['score_credito']}. Perguntar como pode ajudar."
        
        state["tentativas_auth"] += 1
        tentativas_restantes = MAX_AUTH_ATTEMPTS - state["tentativas_auth"]
        
        if tentativas_restantes <= 0:
            state["bloqueado"] = True
            return "STATUS: BLOQUEADO. Tentativas esgotadas. Orientar cliente a contatar Central 0800-123-4567."
        
        return f"STATUS: DADOS_INVALIDOS. Tentativas restantes: {tentativas_restantes}. Solicitar novamente CPF e data de nascimento."
    
    return autenticar_cliente

def criar_ferramenta_verificar_auth(session_id: str):
    """
    Cria ferramenta para verificar se cliente está autenticado.
    Usada por todos os agentes para validar sessão.
    """
    
    def verificar_autenticacao() -> str:
        """
        Verifica se o cliente está autenticado na sessão atual.
        
        Use esta ferramenta ANTES de qualquer operação que requer autenticação.
        Retorna informações do cliente se autenticado.
        
        Returns:
            String com o status da autenticação:
            - AUTENTICADO: Inclui nome, CPF e score do cliente
            - NAO_AUTENTICADO: Cliente precisa se identificar
            - BLOQUEADO: Acesso bloqueado, orientar contato com central
        """
        state = get_session_state(session_id)
        
        if state["bloqueado"]:
            return "STATUS: BLOQUEADO. Central: 0800-123-4567."
        
        if state["autenticado"]:
            return f"STATUS: AUTENTICADO. Nome: {state['nome']}. CPF: {state['cpf']}. Score: {state['score_credito']}."
        
        return "STATUS: NAO_AUTENTICADO. Solicitar CPF e data de nascimento."
    
    return verificar_autenticacao

# FERRAMENTAS DE CRÉDITO (LIMITE)

def _formatar_reais(valor: float) -> str:
    """
    Formata um valor numérico para o padrão brasileiro de moeda.
    
    Exemplo: 15000.50 -> "R$ 15.000,50"
    """
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def criar_ferramenta_consultar_limite(session_id: str):
    """
    Cria ferramenta de consulta de limite vinculada à sessão.
    Usada pelo Agente de Crédito.
    """
    
    def consultar_limite_credito() -> str:
        """
        Consulta o limite de crédito atual do cliente.
        
        O cliente DEVE estar autenticado para usar esta função.
        Retorna o limite formatado em reais brasileiros.
        
        Returns:
            String com o resultado:
            - SUCESSO: Limite atual formatado (ex: R$ 15.000,00)
            - NAO_AUTENTICADO: Cliente precisa se identificar primeiro
            - ERRO: Problema na consulta
        """
        state = get_session_state(session_id)
        
        if not state["autenticado"]:
            return "RESULTADO: NAO_AUTENTICADO. Por favor, identifique-se primeiro com CPF e data de nascimento."
        
        resultado = tools.consultando_limite(state["cpf"])
        
        if resultado["status"] == "ok":
            limite = resultado.get("limite_atual", 0)
            state["limite_atual"] = limite
            valor_formatado = _formatar_reais(limite)
            return f"RESULTADO: SUCESSO. O limite de crédito atual do cliente é {valor_formatado}."
        
        return "RESULTADO: ERRO. Não foi possível consultar o limite. Por favor, tente novamente."
    
    return consultar_limite_credito

def criar_ferramenta_solicitar_limite(session_id: str):
    """
    Cria ferramenta de solicitação de limite vinculada à sessão.
    Usada pelo Agente de Crédito.
    """
    
    def solicitar_aumento_limite(novo_limite: float) -> str:
        """
        Solicita aumento do limite de crédito para o valor especificado.
        
        O cliente DEVE estar autenticado para usar esta função.
        A aprovação depende do score de crédito do cliente.
        
        Args:
            novo_limite: Valor do novo limite desejado em reais (ex: 15000.00 para R$ 15.000,00).
        
        Returns:
            String com o resultado:
            - APROVADO: Novo limite aprovado com sucesso
            - NEGADO: Valor não aprovado, mostra máximo disponível e sugere entrevista
            - NAO_AUTENTICADO: Cliente precisa se identificar primeiro
        """
        state = get_session_state(session_id)
        
        if not state["autenticado"]:
            return "RESULTADO: NAO_AUTENTICADO. Por favor, identifique-se primeiro com CPF e data de nascimento."
        
        resultado = tools.solicitacao_de_limite(state["cpf"], novo_limite)
        
        if resultado["status"] == "ok":
            state["limite_atual"] = resultado.get("novo_limite", novo_limite)
            valor_formatado = _formatar_reais(novo_limite)
            return f"RESULTADO: APROVADO. O novo limite de {valor_formatado} foi aprovado com sucesso."
        
        limite_maximo = resultado.get("limite_maximo_permitido", 0)
        valor_solicitado = _formatar_reais(novo_limite)
        valor_maximo = _formatar_reais(limite_maximo)
        return f"RESULTADO: NEGADO. O limite de {valor_solicitado} não pôde ser aprovado. O valor máximo disponível para seu perfil é {valor_maximo}. Sugestão: realize uma entrevista de crédito para aumentar seu score."
    
    return solicitar_aumento_limite

# FERRAMENTAS DE ENTREVISTA DE CRÉDITO (SCORE)

def criar_ferramenta_entrevista_credito(session_id: str):
    """
    Cria ferramenta de atualização de score após entrevista.
    Usada pelo Agente de Entrevista de Crédito.
    """
    
    def atualizar_score_apos_entrevista(
        renda_mensal: float,
        tipo_emprego: str,
        despesas_mensais: float,
        numero_dependentes: int,
        possui_dividas: str
    ) -> str:
        """
        Atualiza o score de crédito do cliente após coletar informações financeiras.
        
        Use esta função APENAS após coletar TODAS as 5 informações necessárias
        do cliente durante a entrevista de crédito.
        
        Args:
            renda_mensal: Renda mensal do cliente em reais (ex: 5000.00 para R$ 5.000,00).
            tipo_emprego: Tipo de emprego do cliente. Valores aceitos: "formal", "autonomo", "desempregado".
            despesas_mensais: Despesas fixas mensais em reais (ex: 2000.00 para R$ 2.000,00).
            numero_dependentes: Quantidade de dependentes (ex: 0, 1, 2, 3...).
            possui_dividas: Se possui dívidas ativas. Valores aceitos: "sim" ou "nao".
        
        Returns:
            String com o resultado:
            - SUCESSO: Novo score calculado, cliente apto a solicitar novo limite
            - ERRO: Problema no processamento
            - NAO_AUTENTICADO: Cliente precisa se identificar primeiro
        """
        state = get_session_state(session_id)
        
        if not state["autenticado"]:
            return "STATUS: NAO_AUTENTICADO. Autenticação necessária."
        
        resultado = tools.atualizar_score_cliente(
            cpf=state["cpf"],
            renda=renda_mensal,
            tipo_emprego=tipo_emprego,
            despesas_mensais=despesas_mensais,
            dependentes=numero_dependentes,
            tem_dividas=possui_dividas
        )
        
        if resultado["status"] == "ok":
            novo_score = resultado.get("novo_score", 0)
            state["score_credito"] = novo_score
            return f"STATUS: SUCESSO. Novo score: {novo_score} pontos. Cliente apto a solicitar novo limite."
        
        mensagem_erro = resultado.get('mensagem', 'Erro no processamento.')
        return f"STATUS: ERRO. Motivo: {mensagem_erro}"
    
    return atualizar_score_apos_entrevista

# EXPORTAÇÃO DE TODAS AS FERRAMENTAS

__all__ = [
    # Estado
    "get_session_state",
    "limpar_estado_sessao",
    "session_states",
    "MAX_AUTH_ATTEMPTS",
    # Triagem
    "criar_ferramenta_autenticacao",
    "criar_ferramenta_verificar_auth",
    # Crédito
    "criar_ferramenta_consultar_limite",
    "criar_ferramenta_solicitar_limite",
    # Entrevista
    "criar_ferramenta_entrevista_credito",
]
