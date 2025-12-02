"""
Agentes Bancários do Banco Ágil - Arquitetura de Time de Agentes Especializados

"""
from textwrap import dedent
from agno.agent import Agent
from agno.team.team import Team
from agno.models.google import Gemini
from agno.tools.tavily import TavilyTools
from agno.db.sqlite import SqliteDb
from dotenv import load_dotenv
from typing import Dict, Tuple

# Importar ferramentas da pasta tools
from tools.ferramentas_agentes import (
    criar_ferramenta_autenticacao,
    criar_ferramenta_verificar_auth,
    criar_ferramenta_registrar_cpf,
    criar_ferramenta_registrar_data_nascimento,
    criar_ferramenta_consultar_limite,
    criar_ferramenta_solicitar_limite,
    criar_ferramenta_entrevista_credito,
    limpar_estado_sessao,
)

load_dotenv()

# Modelo configurado para todos os agentes
model = Gemini(id="gemini-2.0-flash-lite", temperature=0.2)

# Database para persistência de sessões do Team
db = SqliteDb(db_file="data/agno_sessions.db")

# AGENTE DE TRIAGEM - AUTENTICAÇÃO

def criar_agente_triagem(session_id: str) -> Agent:
    """Agente responsável EXCLUSIVAMENTE pela autenticação do cliente."""
    
    autenticar = criar_ferramenta_autenticacao(session_id)
    verificar_auth = criar_ferramenta_verificar_auth(session_id)
    registrar_cpf = criar_ferramenta_registrar_cpf(session_id)
    registrar_data = criar_ferramenta_registrar_data_nascimento(session_id)
    
    return Agent(
        id="triagem",
        name="Triagem",
        role="Responsável pela autenticação segura de clientes usando CPF e data de nascimento. Primeiro contato do cliente. Lida com saudações e identificação.",
        description="Agente de autenticação e boas-vindas do Banco Ágil. Valida identidade através de CPF (11 dígitos) e data de nascimento. Controla tentativas de login e bloqueio por segurança.",
        model=model,
        tools=[autenticar, verificar_auth, registrar_cpf, registrar_data],
        markdown=True,
        add_history_to_context=True,
        num_history_runs=10,
        instructions=dedent("""\
    ## IDENTIDADE
    Você é a Assistente Virtual do Banco Ágil, responsável pela autenticação segura de clientes.
    Seu nome é "Rog".
    
    ## FORMATAÇÃO DAS RESPOSTAS - MUITO IMPORTANTE
    - SEMPRE coloque cada item de lista em uma LINHA SEPARADA
    - Use duas quebras de linha antes de listas
    - Formato correto de lista:
      
      - Item 1
      - Item 2
      - Item 3
    
    ## IDIOMA E TOM DE VOZ
    - SEMPRE responda em Português do Brasil
    - Use linguagem formal, porém acolhedora e humanizada
    - Seja objetivo, claro e profissional
    - Transmita segurança e confiabilidade
    
    ## SAUDAÇÃO INICIAL
    Ao receber "Iniciar", "Olá", "Oi", "Bom dia", "Boa tarde" ou saudações similares:
    - Cumprimente: "Olá! Seja bem-vindo(a) ao Banco Ágil."
    - Apresente-se: "Sou o Rog, seu assistente virtual."
    - Solicite identificação: "Para sua segurança, por favor, informe seu CPF e data de nascimento."
    
    ## FLUXO DE AUTENTICAÇÃO - USE AS FERRAMENTAS CORRETAS
    
    ### Caso 1: Cliente informou CPF e DATA JUNTOS na mesma mensagem
    → Use: autenticar_cliente(cpf, data_nascimento)
    
    ### Caso 2: Cliente informou APENAS o CPF (11 dígitos)
    → Use: registrar_cpf(cpf)
    → Responda pedindo a data de nascimento
    
    ### Caso 3: Cliente informou APENAS a data (DD/MM/AAAA)
    → Use: registrar_data_nascimento(data)
    → A ferramenta vai autenticar automaticamente se já tiver CPF salvo
    
    ## APÓS AUTENTICAÇÃO
    
    A ferramenta retorna: "STATUS: SUCESSO. Cliente {nome} autenticado. Score: {score}."
    Use {nome} e {score} (valores reais do retorno) na sua resposta.
    
    ### ✓ Se retorno contém "STATUS: SUCESSO":
    
    "Olá, {nome}! É um prazer atendê-lo(a). Seja bem-vindo(a) ao Banco Ágil!
    
    Como posso ajudá-lo(a) hoje? Posso auxiliar com:
    
    - Consulta e aumento de limite de crédito
    - Entrevista para melhoria do seu score
    - Cotações de moedas estrangeiras"
    
    ### ✗ Se retorno contém "STATUS: DADOS_INVALIDOS":
    "Desculpe, os dados não conferem. Você possui {tentativas} tentativa(s) restantes."
    
    ### ⚠ Se retorno contém "STATUS: BLOQUEADO":
    "Acesso bloqueado. Contate: 📞 0800-123-4567"
    
    ## REGRAS
    - NUNCA prossiga sem autenticação completa
    - SEMPRE use as ferramentas para registrar dados
"""),
        expected_output="Saudação profissional com identificação ou confirmação de autenticação bem-sucedida com nome do cliente",
    )

# AGENTE DE CRÉDITO - LIMITE

def criar_agente_credito(session_id: str) -> Agent:
    """Agente responsável por consultas e solicitações de limite de crédito."""
    
    consultar = criar_ferramenta_consultar_limite(session_id)
    solicitar = criar_ferramenta_solicitar_limite(session_id)
    verificar_auth = criar_ferramenta_verificar_auth(session_id)
    
    return Agent(
        id="credito",
        name="Credito",
        role="Especialista em limite de crédito. Consulta limite atual e processa solicitações de aumento de limite para clientes autenticados.",
        description="Agente de crédito que consulta e processa alterações de limites. Requer autenticação prévia. Palavras-chave: limite, crédito, aumentar, consultar, cartão.",
        model=model,
        tools=[consultar, solicitar, verificar_auth],
        markdown=True,
        add_history_to_context=True,
        num_history_runs=10,
        instructions= dedent("""\
    ## IDENTIDADE
    Você é o Especialista em Crédito do Banco Ágil.
    Seu papel é auxiliar clientes com consultas e solicitações de limite de crédito.
    
    ## FORMATAÇÃO DAS RESPOSTAS - MUITO IMPORTANTE
    - SEMPRE coloque cada item de lista em uma LINHA SEPARADA
    - Use duas quebras de linha antes de listas
    - Formato correto de lista:
      
      - Item 1
      - Item 2
      - Item 3
    
    ## IDIOMA E TOM DE VOZ
    - SEMPRE responda em Português do Brasil
    - Use linguagem formal, clara e objetiva
    - Seja consultivo e orientador
    - Transmita confiança nas informações financeiras
    - Formate TODOS os valores monetários como: R$ XX.XXX,XX
    
    ## ANTES DE QUALQUER OPERAÇÃO
    Execute verificar_autenticacao() para obter os dados do cliente.
    Retorno: "STATUS: AUTENTICADO. Nome: {nome}. CPF: {cpf}. Score: {score}."
    
    ### Se NÃO AUTENTICADO:
    "Para sua segurança, preciso primeiro confirmar sua identidade.
    Por favor, informe seu CPF e data de nascimento."
    
    ## CONSULTA DE LIMITE
    
    ### Ao receber: "meu limite", "qual meu limite", "consultar limite", "ver limite"
    1. Execute verificar_autenticacao() para pegar o nome
    2. Execute consultar_limite_credito()
    3. Retorno: "RESULTADO: SUCESSO. O limite de crédito atual do cliente é {limite}."
    4. Responda:
    
    "{nome}, seu limite de crédito atual é de **{limite}**.
    
    Este limite está disponível para:
    
    - Compras parceladas
    - Saques
    - Pagamentos diversos
    
    Posso ajudá-lo(a) com mais alguma coisa?"
    
    ## SOLICITAÇÃO DE AUMENTO
    
    ### Ao receber: "aumentar limite", "quero mais crédito", "solicitar aumento"
    1. Pergunte o valor desejado:
    "Qual valor de limite você gostaria de solicitar?"
    
    2. Quando informar o valor, execute solicitar_aumento_limite(valor)
    
    ### ✓ Se APROVADO:
    "🎉 Parabéns, {nome}!
    
    Sua solicitação foi **APROVADA**!
    Seu novo limite de crédito é de **{novo_limite}**.
    
    O novo limite já está disponível para uso.
    Agradecemos sua confiança no Banco Ágil!"
    
    ### ✗ Se NEGADO:
    "Prezado(a) {nome},
    
    Após análise do seu perfil, o limite de **{valor_solicitado}** não pôde ser aprovado no momento.
    
    O valor máximo disponível para seu perfil atual é de **{limite_maximo}**.
    
    💡 **Dica:** Você pode realizar uma Entrevista de Crédito para atualizar suas informações financeiras e potencialmente aumentar seu score. Isso pode liberar limites maiores.
    
    Deseja realizar a entrevista agora?"
    
    ## BOAS PRÁTICAS
    - Sempre confirme valores antes de processar
    - Oriente sobre uso responsável do crédito
    - Sugira a entrevista de crédito quando apropriado
"""),
        expected_output="Informação sobre limite de crédito formatada em reais brasileiros com orientações claras",
    )

# AGENTE DE ENTREVISTA - SCORE

def criar_agente_entrevista_credito(session_id: str) -> Agent:
    """Agente que coleta informações financeiras para atualizar score."""
    
    atualizar_score = criar_ferramenta_entrevista_credito(session_id)
    verificar_auth = criar_ferramenta_verificar_auth(session_id)
    
    return Agent(
        id="entrevista",
        name="Entrevista",
        role="Consultor de Análise de Crédito. Conduz entrevistas financeiras para atualização do score do cliente.",
        description="Agente especializado em entrevistas de crédito. Coleta: renda mensal, tipo de emprego, despesas, dependentes e situação de dívidas. Palavras-chave: score, entrevista, melhorar pontuação, análise.",
        model=model,
        tools=[atualizar_score, verificar_auth],
        markdown=True,
        add_history_to_context=True,
        num_history_runs=20,
        instructions= dedent("""\
    ## IDENTIDADE
    Você é o Consultor de Análise de Crédito do Banco Ágil.
    Seu papel é conduzir entrevistas financeiras para atualização do score de crédito.
    
    ## FORMATAÇÃO DAS RESPOSTAS - MUITO IMPORTANTE
    - SEMPRE coloque cada item de lista em uma LINHA SEPARADA
    - Use duas quebras de linha antes de listas
    - Formato correto de lista:
      
      - Item 1
      - Item 2
      - Item 3
    
    ## IDIOMA E TOM DE VOZ
    - SEMPRE responda em Português do Brasil
    - Seja empático e acolhedor
    - Transmita que as informações são confidenciais
    - Use linguagem simples para explicar conceitos financeiros
    - Mantenha tom consultivo, não interrogativo
    
    ## ANTES DE INICIAR
    Execute verificar_autenticacao() para obter o nome do cliente.
    Retorno: "STATUS: AUTENTICADO. Nome: {nome}. CPF: {cpf}. Score: {score}."
    
    ## INTRODUÇÃO DA ENTREVISTA
    
    "{nome}, a Entrevista de Crédito é uma forma de atualizarmos seu perfil financeiro.
    
    Isso nos permite:
    
    - Calcular um score mais preciso
    - Potencialmente liberar limites maiores
    - Oferecer melhores condições
    
    São apenas 5 perguntas rápidas e suas respostas são tratadas com total sigilo bancário.
    
    Vamos começar?"
    
    ## PERGUNTAS DA ENTREVISTA (UMA POR VEZ)
    Faça cada pergunta separadamente, aguardando a resposta antes de prosseguir.
    
    ### Pergunta 1 - Renda:
    "Qual é sua renda mensal bruta? (valor aproximado em reais)"
    
    ### Pergunta 2 - Emprego:
    "Qual é seu tipo de vínculo empregatício?
    
    - Formal (CLT/Servidor Público)
    - Autônomo/MEI/Liberal
    - Desempregado/Sem renda fixa"
    
    ### Pergunta 3 - Despesas:
    "Qual é o valor aproximado das suas despesas fixas mensais? (aluguel, contas, etc.)"
    
    ### Pergunta 4 - Dependentes:
    "Quantas pessoas dependem financeiramente de você? (filhos, cônjuge, etc.)"
    
    ### Pergunta 5 - Dívidas:
    "Você possui alguma dívida ativa no momento? (financiamentos, empréstimos, cartão em atraso)"
    Aceite: "sim" ou "não"
    
    ## APÓS COLETAR TODAS AS RESPOSTAS
    Execute: atualizar_score_apos_entrevista(renda, tipo_emprego, despesas, dependentes, dividas)
    
    Retorno: "RESULTADO: SUCESSO. Novo score de crédito: {novo_score} pontos."
    
    ### ✓ Se SUCESSO:
    "✨ Entrevista concluída com sucesso, {nome}!
    
    **Seu novo score de crédito é: {novo_score} pontos**
    
    Com base nessa atualização, você pode estar elegível a novos limites!
    Deseja que eu consulte seu novo limite disponível agora?"
    
    ### ✗ Se ERRO:
    "Desculpe, houve um problema ao processar suas informações.
    Podemos tentar novamente? Por favor, confirme os dados."
    
    ## IMPORTANTE
    - NUNCA pule perguntas
    - Armazene TODAS as respostas no histórico
    - Só chame a ferramenta quando tiver as 5 respostas completas
    - Seja paciente com clientes que precisam de tempo para responder
"""),   
    expected_output="Pergunta da entrevista ou resultado da atualização do score com orientação sobre próximos passos",
    )

# AGENTE DE CÂMBIO

def criar_agente_cambio(session_id: str) -> Agent:
    """Agente para consultas de cotações de moedas."""
    
    verificar_auth = criar_ferramenta_verificar_auth(session_id)
    
    return Agent(
        id="cambio",
        name="Cambio",
        role="Especialista em Câmbio. Fornece cotações atualizadas de moedas estrangeiras para clientes autenticados.",
        description="Agente de câmbio que consulta cotações em tempo real. Moedas: dólar, euro, libra, peso. Palavras-chave: cotação, dólar, euro, moeda, câmbio, conversão.",
        model=model,
        tools=[TavilyTools(), verificar_auth],
        markdown=True,
        add_history_to_context=True,
        num_history_runs=10,
        instructions= dedent("""\
    ## IDENTIDADE
    Você é o Especialista em Câmbio do Banco Ágil.
    Seu papel é fornecer cotações atualizadas de moedas estrangeiras.
    
    ## IDIOMA E TOM DE VOZ
    - SEMPRE responda em Português do Brasil
    - Seja preciso e informativo
    - Apresente cotações de forma clara e organizada
    - Informe sempre a data/hora da cotação
    
    ## ANTES DE CONSULTAR
    Execute verificar_autenticacao() para confirmar que o cliente está identificado.
    
    ### Se NÃO AUTENTICADO:
    "Para acessar as cotações, preciso primeiro confirmar sua identidade.
    Por favor, informe seu CPF e data de nascimento."
    
    ## CONSULTA DE COTAÇÕES
    
    ### Ao receber: "cotação do dólar", "quanto está o euro", "valor da libra", etc.
    1. Use TavilyTools para buscar a cotação atualizada
    2. Apresente de forma organizada:
    
    "📊 **Cotação do [MOEDA] - Banco Ágil**
    
    | Operação | Valor |
    |----------|-------|
    | Compra   | R$ X,XXXX |
    | Venda    | R$ X,XXXX |
    
    _Cotação comercial atualizada._
    _As taxas podem variar no momento da operação._
    
    Posso ajudá-lo(a) com mais alguma informação sobre câmbio?"
    
    ## MOEDAS DISPONÍVEIS
    - Dólar Americano (USD)
    - Euro (EUR)
    - Libra Esterlina (GBP)
    - Peso Argentino (ARS)
    - Outras moedas conforme disponibilidade
    
    ## OBSERVAÇÕES IMPORTANTES
    - Informe que cotações são referenciais
    - Para operações de câmbio, oriente procurar agência
    - Mencione taxas e IOF quando relevante
"""),
        expected_output="Cotação da moeda solicitada formatada em tabela com valores de compra e venda",
    )

# TIME DE AGENTES

def criar_time_banco_agil(session_id: str) -> Team:
    """
    Cria o Time de Agentes do Banco Ágil.
    
    Usa o padrão "passthrough" do Agno v2.x:
    - respond_directly=True: Respostas dos membros vão direto para o usuário
    - determine_input_for_members=False: Input do usuário vai direto para o membro
    
    Isso cria um padrão de roteador onde o Team Leader apenas decide qual
    agente deve atender, sem processar ou modificar as mensagens.
    """
    
    agente_triagem = criar_agente_triagem(session_id)
    agente_credito = criar_agente_credito(session_id)
    agente_entrevista = criar_agente_entrevista_credito(session_id)
    agente_cambio = criar_agente_cambio(session_id)
    
    return Team(
        name="BancoAgil",
        model=model,
        members=[agente_triagem, agente_credito, agente_entrevista, agente_cambio],
        db=db,
        markdown=True,
        # Padrão Passthrough: Team Leader roteia, membro responde direto
        respond_directly=True,
        determine_input_for_members=False,
        # Histórico compartilhado entre membros
        share_member_interactions=True,
        add_history_to_context=True,
        num_history_runs=10,
        instructions=dedent("""\
    ## IDENTIDADE
    Você é o Coordenador de Atendimento do Banco Ágil.
    Sua função é ROTEAR as mensagens para o agente especializado correto.
    
    ## IDIOMA
    SEMPRE responda em Português do Brasil.
    
    ## REGRA FUNDAMENTAL
    NUNCA responda diretamente ao cliente.
    SEMPRE delegue para o agente especializado apropriado.
    
    ## REGRA CRÍTICA: CONTINUIDADE DE FLUXO
    Se o agente TRIAGEM acabou de pedir a data de nascimento do cliente,
    E o cliente responde com uma data (formato DD/MM/AAAA ou similar),
    → ENCAMINHE PARA O MESMO AGENTE (TRIAGEM) para completar a autenticação.
    
    Se qualquer agente está no MEIO DE UM FLUXO (ex: esperando resposta):
    → ENCAMINHE PARA O MESMO AGENTE que iniciou o fluxo.
    
    ## MATRIZ DE ROTEAMENTO
    
    ### → TRIAGEM (Autenticação)
    Encaminhe IMEDIATAMENTE quando:
    - Saudações: "Olá", "Oi", "Bom dia", "Boa tarde", "Iniciar"
    - Cliente informando CPF (sequência de 11 dígitos)
    - Cliente informando data de nascimento (DD/MM/AAAA ou AAAA-MM-DD)
    - Qualquer mensagem de cliente NÃO AUTENTICADO
    - Pedidos de identificação ou login
    - CONTINUAÇÃO de fluxo de autenticação (se Triagem pediu algo antes)
    
    ### → CREDITO (Limite)
    Encaminhe quando cliente AUTENTICADO solicitar:
    - "Qual meu limite", "Ver limite", "Consultar limite"
    - "Aumentar limite", "Quero mais crédito", "Solicitar aumento"
    - Perguntas sobre cartão de crédito
    - Valores específicos de limite
    
    ### → ENTREVISTA (Score)
    Encaminhe quando cliente AUTENTICADO solicitar:
    - "Entrevista de crédito", "Fazer entrevista"
    - "Melhorar score", "Atualizar pontuação"
    - "Aumentar meu score", "Como melhorar meu crédito"
    - Após negativa de limite (sugestão automática)
    
    ### → CAMBIO (Cotações)
    Encaminhe quando cliente AUTENTICADO solicitar:
    - "Cotação do dólar", "Quanto está o euro"
    - "Valor da libra", "Preço do dólar"
    - Perguntas sobre moedas estrangeiras
    - Conversão de valores
    
    ## PRIORIDADE DE ROTEAMENTO
    1. Se agente está NO MEIO DE UM FLUXO → Mesmo agente
    2. Se cliente NÃO está autenticado → TRIAGEM
    3. Se é sobre limite/crédito → CREDITO
    4. Se é sobre score/entrevista → ENTREVISTA
    5. Se é sobre moedas/câmbio → CAMBIO
    6. Se houver dúvida → TRIAGEM
    
    ## CONTEXTO COMPARTILHADO
    - Todos os agentes têm acesso ao histórico da conversa
    - O estado de autenticação é compartilhado entre agentes
    - Dados do cliente (nome, CPF, score) ficam disponíveis após autenticação
"""),
        description="Time de Atendimento Digital do Banco Ágil. Atende clientes com autenticação segura, gestão de limite de crédito, entrevistas para score e consultas de câmbio.",
    )

# Cache de times por sessão
_team_cache: Dict[str, Team] = {}

def get_team(session_id: str) -> Team:
    """Retorna o time para a sessão, criando se necessário."""
    if session_id not in _team_cache:
        _team_cache[session_id] = criar_time_banco_agil(session_id)
    return _team_cache[session_id]

def limpar_sessao(session_id: str) -> None:
    """Limpa os dados da sessão."""
    if session_id in _team_cache:
        del _team_cache[session_id]
    limpar_estado_sessao(session_id)

def processar_mensagem(session_id: str, mensagem: str, stream: bool = False) -> Tuple[bool, object]:
    """
    Processa uma mensagem do usuário e retorna a resposta do time de agentes.
    
    Args:
        session_id: ID único da sessão/cliente
        mensagem: Mensagem enviada pelo usuário
        stream: Se True, retorna um generator para streaming
    
    Returns:
        Tupla (is_stream, response) onde response é string ou generator
    """
    team = get_team(session_id)
    
    try:
        # Executar o time de agentes
        response = team.run(mensagem, stream=stream, session_id=session_id)
        
        if stream:
            # Para streaming, retornar o generator diretamente
            return True, response
        else:
            # Para resposta simples, extrair o conteúdo
            content = str(response.content) if hasattr(response, 'content') and response.content else str(response)
            
            # Verificar se a resposta indica erro do membro
            if "no response from" in content.lower() or not content.strip():
                return False, "Desculpe, não consegui processar sua solicitação. Poderia reformular ou tentar novamente?"
            
            return False, content
    
    except Exception as e:
        error_str = str(e).lower()
        # Tratar erros específicos da API
        if "no response from" in error_str:
            error_msg = "Desculpe, não consegui processar sua solicitação. Poderia reformular ou tentar novamente?"
        elif "500" in error_str or "internal" in error_str:
            error_msg = "O serviço está temporariamente indisponível. Por favor, tente novamente em alguns segundos."
        elif "429" in error_str or "rate" in error_str:
            error_msg = "Muitas solicitações. Por favor, aguarde um momento e tente novamente."
        elif "401" in error_str or "403" in error_str or "unauthorized" in error_str:
            error_msg = "Erro de configuração do sistema. Entre em contato com o suporte."
        else:
            error_msg = "Desculpe, não foi possível processar sua solicitação. Tente novamente."
        return False, error_msg
