import pandas as pd
import os

def criar_dados_csv():
    """Cria arquivos CSV apenas se não existirem (não sobrescreve dados existentes)."""
    # Verificando a existencia da pasta 'data'
    if not os.path.exists('data'):
        os.makedirs('data')

    # Base de clientes - só cria se não existir
    clientes_path = 'data/clientes.csv'
    if not os.path.exists(clientes_path):
        clientes_data = {
            "cpf": ["12345678901", "98765432100", "11122233344"],
            "nome": ["Guilherme Fernandes", "Leci Cardoso", "Safira Cardoso"],
            "dt_nascimento": ["1995-02-13", "1996-08-16", "2000-11-07"],
            "score_credito": [750, 680, 720],
            "renda_mensal": [5000.00, 3000.00, 4500.00],
            "limite_credito": [15000.00, 9000.00, 13500.00]
        }
        clientes_df = pd.DataFrame(clientes_data)
        clientes_df.to_csv(clientes_path, index=False)
        print(f"Criado: {clientes_path}")
    else:
        print(f"Mantido existente: {clientes_path}")

    # Base de Score de Crédito - só cria se não existir
    score_path = 'data/score_credito_base.csv'
    if not os.path.exists(score_path):
        score_base_data = {
            "score_min": [0, 300, 600, 800],
            "score_max": [299, 599, 799, 1000],
            "limite_maximo": [0, 1000, 5000, 20000],
        }
        score_base_df = pd.DataFrame(score_base_data)
        score_base_df.to_csv(score_path, index=False)
        print(f"Criado: {score_path}")
    else:
        print(f"Mantido existente: {score_path}")

    # Arquivo de Solicitações de Crédito
    solicitacoes_path = 'data/solicitacoes_aumento_limite.csv'
    if not os.path.exists(solicitacoes_path):
        df_colunas = pd.DataFrame(
            columns=["cpf_cliente", "data_hora_solicitacao", "limite_atual", "novo_limite_solicitado", "status_pedido"]
        )
        df_colunas.to_csv(solicitacoes_path, index=False)
        print(f"Criado: {solicitacoes_path}")
    else:
        print(f"Mantido existente: {solicitacoes_path}")

    print("Inicialização de dados concluída.")

if __name__ == "__main__":
    criar_dados_csv()