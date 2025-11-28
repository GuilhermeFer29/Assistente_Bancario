import pandas as pd
import datetime
import re

cliente_db = "data/clientes.csv"
solicitacoes_db = "data/solicitacoes_aumento_limite.csv"
scores_db = "data/score_credito_base.csv"

def limpar_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos do CPF."""
    return re.sub(r'\D', '', str(cpf))

def normalizar_data(data_str: str) -> str:
    """Tenta converter a data para o formato YYYY-MM-DD."""
    try:
        # Remove espaços extras
        data_str = data_str.strip()
        
        # Tenta converter usando pandas, forçando dayfirst=True para formatos como DD/MM/YYYY
        # e errors='coerce' para retornar NaT se falhar
        dt = pd.to_datetime(data_str, dayfirst=True, errors='coerce')
        
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
        return data_str
    except:
        return data_str

def validando_cliente(cpf: str, dt_nascimento: str)-> str:
    """Aqui vamos validar o CPF a Data de Nascimento para conferir se batem com a base de dados em CSV"""

    try:
        cpf_limpo = limpar_cpf(cpf)
        data_normalizada = normalizar_data(dt_nascimento)
        
        df_clientes = pd.read_csv(cliente_db, dtype=str)
        
        cliente = df_clientes[
            (df_clientes['cpf'] == cpf_limpo) & 
            (df_clientes['dt_nascimento'] == data_normalizada)
        ]

        # IF de cliente encontrado

        if not cliente.empty:
            return f"Cliente Autenticado: Nome: {cliente.iloc[0]['nome']}. Score Atual: {cliente.iloc[0]['score_credito']}."
        else:
            return f"Cliente não encontrado. Verifique os dados informados. (CPF processado: {cpf_limpo}, Data processada: {data_normalizada})"
    except Exception as e:
        return f"Erro ao validar cliente: {str(e)}"

def consultando_limite(cpf:str) -> str:
    """"Aqui iremos verificar o Limite atual do cliente na base de dados CSV""" 
    try:
        cpf_limpo = limpar_cpf(cpf)
        df_clientes = pd.read_csv(cliente_db, dtype=str)
        cliente = df_clientes[df_clientes['cpf'] == cpf_limpo]

        # IF de cliente encontrado

        if not cliente.empty:
            return f"Limite Atual do Cliente {cliente.iloc[0]['nome']}: R$ {cliente.iloc[0]['limite_credito']}."
        else:
            return f"Cliente não encontrado. Verifique o CPF informado. (CPF processado: {cpf_limpo})"
    except Exception as e:
        return f"Erro ao consultar limite: {str(e)}"

def solicitacao_de_limite(cpf: str, novo_limite: float) -> str:
    """Aqui vamos processar a solicitação de um novo credito baseado no score do cliente""" 

    # Lendo os dados dos clientes e scores
    cpf_limpo = limpar_cpf(cpf)
    df_clientes = pd.read_csv(cliente_db, dtype={'cpf': str})
    df_scores = pd.read_csv(scores_db)
    cliente = df_clientes[df_clientes['cpf'] == cpf_limpo]

    if cliente.empty:
        return f"Cliente não encontrado. Verifique o CPF informado. (CPF processado: {cpf_limpo})"
    score_atual_cliente = float(cliente.iloc[0]['score_credito'])
    limite_atual_cliente = float(cliente.iloc[0]['limite_credito'])

    # Verificação da regra de score para aprovação do novo limite
    status_solicitacao = "Rejeitado"
    for index, row in df_scores.iterrows():
        if row ['score_minimo'] <= score_atual_cliente <= row['score_minimo']:
            if novo_limite <= row['limite_maximo']:
                status_solicitacao = "Aprovado"
            break

    # Registrar a solicitação no CSV
    nova_solicitacao={
        'cpf_cliente':cpf,
        'data_hora_solicitacao': datetime.datetime.now().isoformat(),
        'limite_atual': limite_atual_cliente,
        'novo_limite_solicitado': novo_limite,
        'status_solicitacao': status_solicitacao
    }    
    
    df_solicitacoes = pd.read_csv(solicitacoes_db)
    df_solicitacoes = pd.concat([df_solicitacoes, pd.DataFrame([nova_solicitacao])], ignore_index=True)
    df_solicitacoes.to_csv(solicitacoes_db, index=False)

    # Informando o resultado atraves de IF da solicitação
    if status_solicitacao == "Aprovado":
        df_clientes.loc[df_clientes['cpf'] == cpf, 'limite_credito'] = novo_limite
        df_clientes.to_csv(cliente_db, index=False)
        return f"Solicitação Aprovada! Novo limite de crédito: R$ {novo_limite}."
    else:
        return "Solicitação Rejeitada. O novo limite solicitado excede o permitido para o seu score de crédito."

def atualizar_score_cliente(cpf: str, renda: float, tipo_emprego: str,despesas_mensais: float, dependentes: int, tem_dividas: str) -> str:
    """Aqui vamos atualizar o score do cliente com base na entrevista feita pelo atendente"""

    # regras de peso conforme o desafio
    peso_renda = 30
    peso_emprego = {"formal": 300, "autonomo": 200, "desempregado": 0}
    peso_dividas = {"sim": -100, "nao": 100}

    # Validando informação estritamente para evitar erros
    tipo_emprego_input = tipo_emprego.lower()
    if tipo_emprego_input not in peso_emprego:
        opcoes=list(peso_emprego.keys())
        # Retorno para o Agente para classificar corretamente a resposta do usuário
        return f" O tipo de emprego '{tipo_emprego}' é inválido. O Agente deve classificar a resposta do usuário em uma destas opções: {opcoes}."

    tem_dividas_input = tem_dividas.lower()
    if tem_dividas_input not in peso_dividas:
        opcoes=list(peso_dividas.keys())
        # Retorno para o Agente para classificar corretamente a resposta do usuário
        return f" A resposta sobre dívidas '{tem_dividas}' é inválida. O Agente deve classificar a resposta do usuário em uma destas opções: {opcoes}."
    
    #Validando renda mensal e dependentes
    if renda < 0 or despesas_mensais < 0:
        return "Renda mensal e número de dependentes não podem ser negativos."
    if dependentes < 0:
        return "Número de dependentes não pode ser negativo."
    
    # Atribuindo valores depois de validados
    valor_emprego = peso_emprego[tipo_emprego_input]
    valor_dividas = peso_dividas[tem_dividas_input]

    # Regra dos dependentes
    if dependentes == 0: valor_depedentes = 100
    elif dependentes == 1: valor_depedentes = 80
    elif dependentes == 2: valor_depedentes = 60
    else: valor_depedentes = 30 # Retorno de 3 ou mais dependentes

    # Formula para o Calculo do Score com base no Desafio PDF

    termo_financeiro = (renda / (despesas_mensais + 1)) * peso_renda
    att_score = (termo_financeiro + valor_emprego + valor_dividas + valor_depedentes)

    # Calculando o score de 0 a 1000
    novo_score = int(min(1000, max(0, att_score)))

    #Tratamento de  erro e persistencia do novo score
    try:
        cpf_limpo = limpar_cpf(cpf)
        df_clientes = pd.read_csv(cliente_db, dtype={'cpf': str})
        if cpf_limpo in df_clientes['cpf'].values:
            df_clientes.loc[df_clientes['cpf'] == cpf_limpo, 'score_credito'] = novo_score
            df_clientes.to_csv(cliente_db, index=False)
            return f"Score atualizado com sucesso! Novo score de crédito: {novo_score}."
        else:
            return f"Cliente não encontrado. Verifique o CPF informado. (CPF processado: {cpf_limpo})"
    except Exception as e:
        return f"Erro ao atualizar score: {str(e)}" 







    

    