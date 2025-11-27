import pandas as pd
import os

def criar_dados_csv():
    # Verificando a existencia da pasta 'data'
    if not os.path.exists('data'):
        os.makedirs('data')

    # Base de clientes exemplos 
    clientes_data ={
        "cpf": ["12345678901", "98765432100", "11122233344"],
        "nome": ["Guilherme Fernandes", "Leci Cardoso ", "Safira Cardoso"],
        "dt_nascimento": ["1995-02-13", "1996-08-16", "2000-11-07"],
        "score_credito": [750, 680, 720],
        "renda_mensal": [5000.00, 3000.00, 4500.00],
        "limite_credito": [15000.00, 9000.00, 13500.00]
    }
    clientes_df = pd.DataFrame(clientes_data)
    clientes_df.to_csv('data/clientes.csv', index=False)

    # Base de Score de Crédito para Análise
    score_base_data = {
        "score_min": [0, 300, 600, 800],
        "score_max": [299, 599, 799, 1000],
        "limite_maximo": [0, 1000,5000, 20000],
    }
    score_base_df = pd.DataFrame(score_base_data)
    score_base_df.to_csv('data/score_credito_base.csv', index=False)
    
    # Arquivo de Solicitaçoes de Crédito
    if not os.path.exists('data/solicitaçoes_aumento_limite.csv'):
        df_colunas = pd.DataFrame(columns=["cpf_cliente", "data_hora_solicitacao", "limite_atual", "novo_limite_solicitado", "status_pedido"])
        df_colunas.to_csv('data/solicitaçoes_aumento_limite.csv', index=False)  

    print("Arquivos CSV gerados na pasta 'data/' com sucesso.")

if __name__ == "__main__":
    criar_dados_csv()