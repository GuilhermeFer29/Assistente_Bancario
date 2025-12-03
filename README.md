# 🏦 Assistente Bancário - Banco Ágil

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Agno](https://img.shields.io/badge/Agno-2.3.4-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.123-teal?logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.51-red?logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)

**Assistente Virtual Inteligente com Arquitetura Multi-Agentes**

</div>

---

## 📋 Índice

- [Visão Geral](#-visão-geral)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Funcionalidades Implementadas](#-funcionalidades-implementadas)
- [Desafios Enfrentados e Soluções](#-desafios-enfrentados-e-soluções)
- [Escolhas Técnicas e Justificativas](#-escolhas-técnicas-e-justificativas)
- [Tutorial de Execução](#-tutorial-de-execução)
- [Estrutura do Código](#-estrutura-do-código)
- [Testes](#-testes)

---

## 🎯 Visão Geral

O **Banco Ágil** é um assistente bancário virtual desenvolvido com arquitetura de **Time de Agentes Especializados** utilizando o framework **Agno**. O sistema simula um atendimento bancário completo, oferecendo:

- **Autenticação segura** via CPF e data de nascimento
- **Consulta e solicitação de limite de crédito**
- **Entrevista de crédito** para atualização de score
- **Consulta de cotações de câmbio** em tempo real
- **Interface de chat moderna** com Streamlit
- **Persistência de sessão via websocket e SQLite** com FastAPI

### Objetivos do Projeto

1. Demonstrar arquitetura multi-agentes com delegação inteligente
2. Implementar fluxos bancários realistas com validações de segurança
3. Criar interface de chat moderna e responsiva
4. Garantir persistência de sessão e histórico de conversas

---

## 🏗 Arquitetura do Sistema

### Diagrama de Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Streamlit)                         │
│                    Interface de Chat - Porta 8501                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ WebSocket
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                            │
│                      API REST/WS - Porta 8000                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    WebSocket Manager                         │    │
│  │              Gerencia conexões por client_id                 │    │
│  └─────────────────────────────┬───────────────────────────────┘    │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     TEAM DE AGENTES (Agno)                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   🎯 COORDENADOR (Team Leader)               │    │
│  │         Roteia mensagens para o agente especializado         │    │
│  │              Padrão: Passthrough (respond_directly)          │    │
│  └───────────┬─────────────┬─────────────┬─────────────┬───────┘    │
│              │             │             │             │            │
│              ▼             ▼             ▼             ▼            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │  🔐 TRIAGEM │ │  💳 CRÉDITO │ │ 📋 ENTREVISTA│ │  💱 CÂMBIO  │   │
│  │             │ │             │ │             │ │             │   │
│  │ Autenticação│ │   Limite    │ │   Score     │ │  Cotações   │   │
│  │ CPF + Data  │ │  Consulta   │ │ 5 Perguntas │ │ Tempo Real  │   │
│  │ 3 Tentativas│ │  Aumento    │ │ Atualização │ │ TavilyTools │   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CAMADA DE DADOS                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │ clientes.csv│  │score_credito│  │ solicitacoes_aumento_limite │  │
│  │             │  │  _base.csv  │  │           .csv              │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              SQLite (agno_sessions.db)                       │    │
│  │         Persistência de sessões e histórico Agno             │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Fluxo de Dados

```
1. Usuário envia mensagem via Streamlit
                    ↓
2. WebSocket transmite para FastAPI
                    ↓
3. processar_mensagem() obtém/cria Team
                    ↓
4. Coordenador analisa e roteia para agente
                    ↓
5. Agente especializado executa ferramentas
                    ↓
6. Ferramentas acessam/modificam dados CSV
                    ↓
7. Resposta retorna pelo WebSocket
                    ↓
8. Streamlit renderiza mensagem formatada
```

### Agentes e Responsabilidades

| Agente | ID | Função | Ferramentas |
|--------|-----|--------|-------------|
| **Triagem** | `triagem` | Autenticação do cliente | `autenticar_cliente`, `registrar_cpf`, `registrar_data_nascimento`, `verificar_autenticacao` |
| **Crédito** | `credito` | Consulta e aumento de limite | `consultar_limite_credito`, `solicitar_aumento_limite`, `verificar_autenticacao` |
| **Entrevista** | `entrevista` | Coleta dados e atualiza score | `atualizar_score_apos_entrevista`, `verificar_autenticacao` |
| **Câmbio** | `cambio` | Cotações em tempo real | `TavilyTools` (busca web), `verificar_autenticacao` |

### Padrão Passthrough (Agno v2.x)

O Team utiliza o padrão **Passthrough** para roteamento:

```python
Team(
    respond_directly=True,           # Resposta vai direto para usuário
    determine_input_for_members=False, # Input não é modificado pelo líder
    share_member_interactions=True,   # Histórico compartilhado
)
```

Este padrão garante:
- Respostas mais rápidas (sem processamento intermediário)
- Preservação do tom e formatação de cada agente
- Histórico consistente entre todos os membros

---

## ✨ Funcionalidades Implementadas

### 1. 🔐 Autenticação Segura

- Validação de CPF (11 dígitos) + Data de Nascimento
- Suporte a entrada de dados separados ou juntos (Cliente pode enviar CPF e Data em mensagens distintas)
- **Limite de 3 tentativas** com bloqueio automático
- Persistência de dados parciais na sessão (CPF/Data pendente são salvos em uma variavel de estado por sessão)

```
Fluxo de Autenticação:
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Cliente    │───▶│ registrar_cpf│───▶│ Aguarda Data │
│ informa CPF  │    │   (salva)    │    │              │
└──────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                                               ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Sucesso!   │◀───│  Autentica   │◀───│Cliente informa│
│ Bem-vindo(a) │    │ automaticamente│   │    Data      │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 2. 💳 Gestão de Limite de Crédito

- **Consulta de limite atual** formatado em reais (R$ XX.XXX,XX)
- **Solicitação de aumento** com análise baseada em score
- Aprovação automática se dentro da faixa permitida
- Sugestão de entrevista quando negado

**Tabela de Limites por Score:** (valores fictícios para demonstração que esta nos CSV)

| Score | Limite Máximo |
|-------|---------------|
| 0-299 | R$ 5.000,00 |
| 300-599 | R$ 10.000,00 |
| 600-799 | R$ 15.000,00 |
| 800-1000 | R$ 25.000,00 |

### 3. 📋 Entrevista de Crédito

Coleta 5 informações financeiras para recalcular o score:

1. **Renda mensal bruta** (valor em R$)
2. **Tipo de emprego** (Formal/Autônomo/Desempregado)
3. **Despesas fixas mensais** (valor em R$)
4. **Número de dependentes** (0, 1, 2 ou 3+)
5. **Possui dívidas ativas** (Sim/Não)

**Fórmula do Score:** ( com base no desafio proposto )
```
score = (renda / (despesas + 1)) × 30 
      + bonus_emprego 
      + bonus_dependentes 
      + bonus_dividas
```

| Fator | Valores |
|-------|---------|
| Emprego | Formal: +300, Autônomo: +200, Desempregado: 0 |
| Dependentes | 0: +100, 1: +80, 2: +60, 3+: +30 |
| Dívidas | Não: +100, Sim: -100 |

### 4. 💱 Consulta de Câmbio

- Cotações em tempo real via **TavilyTools** (busca web)
- Moedas suportadas: USD, EUR, GBP, ARS
- Apresentação em tabela com valores de compra e venda
- Avisos sobre taxas e IOF

### 5. 🎨 Interface de Usuário

- **Tema bancário** dark (azul escuro e preto)
- Chat responsivo com avatares diferenciados
- Comandos especiais: `Iniciar` e `Finalizar`
- Exibição de clientes de teste para demonstração
- Sessão com ID único visível

---

## 🧩 Desafios Enfrentados e Soluções

### Desafio 1: Persistência de Dados de Autenticação

**Problema:** O modelo perdia o CPF informado quando o cliente enviava a data de nascimento em uma mensagem separada e reiniciava a conversa .

**Solução:** Criação de ferramentas específicas com estado de sessão, que nos permitiu salvar em variaveis de estado os dados parciais e autenticar quando ambos estivessem presentes.

```python
# Aqui estamos persistindo os dados e salvando ele em um dicionário global por sessão
session_states[session_id] = {
    "cpf_pendente": None,
    "data_nascimento_pendente": None,
}

# Criada uma ferramenta para registrar o CPF do cliente
def registrar_cpf(cpf: str) -> str:
    state["cpf_pendente"] = cpf
    if state["data_nascimento_pendente"]:
        # Já tem data, autenticar!
        return autenticar()
    return "CPF salvo. Informe a data."
```

### Desafio 2: Formatação de Respostas (Listas e Valores)

**Problema:** Os bullet points apareciam na mesma linha, valores monetários não formatados corretamente, textos quebrados.

**Solução:** 
1. Instruções explícitas de formatação para cada agente 
2. Função auxiliar `_formatar_reais()` para valores monetários
3. Uso de hífens `-` em vez de bullets `•` para compatibilidade Markdown
4. Ajustes no frontend Streamlit para renderização correta fazendo a formatação da resposta recebida do modelo (Gemini).

```python
def _formatar_reais(valor: float) -> str:
    """R$ 15.000,50 (padrão brasileiro)"""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
```

### Desafio 3: Tratamento de erros de API 

**Problema:** Comunicação entre a API do Google que retornava os erros (429 -> limite, 404 -> não encontrado).

**Solução:** Ter um tratamento de erro ao processar a mensagem, que quando ele processava a mensagem e recebia um erro da API, ele retornava uma mensagem amigável ao usuário e conexao e fechada na interface.

```python
# agent/agents.py
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
```

### Desafio 4: Contexto Entre Mensagens (Histórico e Memória)

**Problema:** O agente não lembrava de informações anteriores da conversa, não havia persistência de histórico/estado da sessão, e não memorizava preferências ou fatos sobre o cliente entre sessões.

**Solução:** Configuração do Agno com histórico de sessão + **Memória Automática** (`enable_user_memories=True`). O Agno extrai e armazena automaticamente fatos relevantes sobre cada cliente (ex: "prefere atendimento rápido", "interessado em aumento de limite"), isolados por `user_id` (CPF).

```python
Agent(
    add_history_to_context=True,  # Inclui histórico no prompt
    num_history_runs=10,           # Ajustável conforme necessidade
)

Team(
    share_member_interactions=True,  # Compartilha entre agentes
    db=SqliteDb(db_file="..."),      # Persiste em banco de dados SQLite
    enable_user_memories=True,       # Memória automática por cliente
)

# No processar_mensagem, usa CPF como user_id para isolar memórias
response = team.run(mensagem, session_id=session_id, user_id=cpf_autenticado)
```

**Benefícios da Memória Automática:**
- Lembra preferências do cliente entre sessões
- Fatos extraídos automaticamente (sem código adicional)
- Isolamento por CPF (cada cliente tem sua própria memória)
- Persistido no mesmo SQLite das sessões

### Desafio 5: Roteamento para Agente Correto

**Problema:** O coordenador às vezes enviava para o agente errado ou assumia a responsabilidade.

**Solução:** Instruções detalhadas de roteamento com matriz de decisão e palavras-chave para cada agente especializado quanto mais específico melhor.

```python
instructions = """
## MATRIZ DE ROTEAMENTO

### → TRIAGEM
- Saudações, CPF, data de nascimento
- Cliente NÃO autenticado

### → CRÉDITO  
- "limite", "crédito", "aumentar"
- Cliente AUTENTICADO

### → ENTREVISTA
- "score", "entrevista", "melhorar"

### → CÂMBIO
- "dólar", "euro", "cotação"
"""
```

### Desafio 6: Placeholder vs Nome Real

**Problema:** O agente respondia literalmente `[NOME]` em vez do nome do cliente.

**Solução:** Uso de placeholders `{nome}`, `{score}`, `{limite}` com instruções claras de que são valores do retorno das ferramentas para os agentes substituírem na resposta final, para evitar confusão.

```python
instructions = """
A ferramenta retorna: "STATUS: SUCESSO. Cliente {nome} autenticado."
Use {nome} (valor real do retorno) na sua resposta.
"""
```

---

## 🔧 Escolhas Técnicas e Justificativas

### Framework de Agentes: Agno v2.3.4
O Agno foi escolhido por sua arquitetura robusta de multi-agentes, facilidade na criação de Teams e integração com modelos de linguagem modernos, e sua facilidade em criar ferramentas com docstrings claras, que facilitou a implementação das funcionalidades bancárias.

| Critério | Justificativa |
|----------|---------------|
| **Multi-agentes** | Suporte nativo a Teams com roteamento |
| **Ferramentas** | Fácil criação de tools com docstrings |
| **Histórico** | Persistência automática em SQLite |
| **Modelos** | Integração com Gemini, OpenAI, etc. |


### Modelo de IA: Gemini 2.0 Flash Lite
Foi escolhido o Gemini 2.0 Flash Lite por sua capacidade de fornecer respostas rápidas e de alta qualidade, essenciais para um assistente bancário que requer precisão e consistência nas interações com os clientes, e na sua disponibilidade via API GRATUITA tendo um RPM(Requisição por minuto) de 30 e um TPM (Tokens por minuto) de 1M e um RPD(Requisições por dia) de 200.

| Critério | Justificativa |
|----------|---------------|
| **Velocidade** | Respostas rápidas para chat |
| **Custo** | Gratuito/baixo custo |
| **Qualidade** | Suficiente para tarefas bancárias |
| **Temperature** | 0.2 (respostas consistentes) |

### Backend: FastAPI

Foi escolhido o FastAPI por sua alta performance, suporte nativo a WebSockets, facilidade de criação de APIs RESTful e documentação automática via Swagger, o que agilizou o desenvolvimento e testes da API do assistente bancário, nos fornecendo uma redução significativa no tempo de desenvolvimento, pois suas ferramentas nativas facilitam a criação de endpoints e a integração com o Agno.

| Critério | Justificativa |
|----------|---------------|
| **WebSocket** | Suporte nativo para chat em tempo real |
| **Async** | Alto throughput de conexões |
| **Validação** | Pydantic integrado |
| **Docs** | Swagger automático |

### Frontend: Streamlit

Streamlit foi escolhido por sua simplicidade na criação de interfaces web interativas, especialmente para aplicações de chat. Sua capacidade de renderizar componentes nativos de chat e personalizar o tema com CSS facilitou a criação de uma interface amigável e responsiva para o assistente bancário.

| Critério | Justificativa |
|----------|---------------|
| **Rapidez** | Protótipo funcional rápido |
| **Chat** | Componentes nativos (`st.chat_*`) |
| **Tema** | CSS customizável |
| **Deploy** | Simples com Docker |

### Armazenamento: CSV + SQLite

Os dados dos clientes e solicitações foram armazenados em arquivos CSV pela sua simplicidade e facilidade de edição manual para demonstração (Conforme Solicitado). Já as sessões do Agno foram persistidas em SQLite para garantir robustez e integridade dos dados das sessões e histórico de interações.

| Dado | Formato | Justificativa |
|------|---------|---------------|
| Clientes | CSV | Fácil edição manual, demonstração |
| Solicitações | CSV | Log simples de operações |
| Sessões Agno | SQLite | Persistência robusta do framework |

### Containerização: Docker Compose

Foi escolhhido o Ambiente Docker Compose para facilitar a implantação e execução do sistema em qualquer máquina, garantindo consistência no ambiente de desenvolvimento e produção, além de simplificar a gestão dos serviços backend e frontend em contêineres separados, para melhor organização e escalabilidade, permitindo que qualquer usuário possa rodar o assistente bancário localmente com poucos comandos.

| Benefício | Descrição |
|-----------|-----------|
| **Isolamento** | Ambiente consistente |
| **Volumes** | Persistência de `/data` |
| **Multi-serviço** | Backend + Frontend juntos |
| **Portabilidade** | Roda em qualquer máquina |

---

## 🚀 Tutorial de Execução

### Pré-requisitos

- **Docker** e **Docker Compose** instalados na máquina (https://hub.docker.com/)
- Chave de API do **Google Gemini** (https://aistudio.google.com/api-keys)
- (Opcional) Chave da **Tavily** para cotações de câmbio(https://app.tavily.com/home)

### Passo a Passo

#### 1. Clone o Repositório

```bash
git clone https://github.com/GuilhermeFer29/Assistente_Bancario.git
cd Assistente_Bancario
```

#### 2. Configure as Variáveis de Ambiente

```bash
# Copie o exemplo
cp .env.example .env

# Edite com suas chaves
nano .env
```

Conteúdo do `.env`:
```env
GOOGLE_API_KEY=sua_chave_gemini_aqui
TAVILY_API_KEY=sua_chave_tavily_aqui  
```

#### 3. Execute com Docker Compose

```bash
# Build e execução
docker compose up -d --build

# Acompanhe os logs
docker compose logs -f
```

#### 4. Acesse a Aplicação

| Serviço | URL |
|---------|-----|
| **Chat (Streamlit)** | http://localhost:8501 |
| **API (FastAPI)** | http://localhost:8000 |
| **Docs Swagger** | http://localhost:8000/docs |

#### 5. Teste o Assistente

**Clientes de Teste Disponíveis:**

> **Nota:** Os valores abaixo refletem o estado atual dos CSVs. Scores e limites podem variar conforme uso do sistema. Ao reiniciar com CSVs vazios, os valores padrão do `scripts/gerador_csv.py` serão aplicados.

| Nome | CPF | Data de Nascimento | Score | Limite Atual |
|------|-----|-------------------|-------|-------------|
| Guilherme Fernandes | `12345678901` | `13/02/1995` | 519 | R$ 10.000,00 |
| Leci Cardoso | `98765432100` | `16/08/1996` | 680 | R$ 5.000,00 |
| Safira Cardoso | `11122233344` | `07/11/2000` | 720 | R$ 5.000,00 |

**Fluxo de Teste Sugerido:**

```
1. Digite: Iniciar
2. Informe: 12345678901
3. Informe: 13/02/1995
4. Peça: Qual meu limite?
5. Solicite: Quero aumentar para 15000
6. Se negado: Fazer entrevista
7. Responda as 5 perguntas
8. Peça: Cotação do dólar
9. Digite: Finalizar
```

### Execução Local (Sem Docker)

```bash
# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Configure variáveis
export GOOGLE_API_KEY=sua_chave

# Execute backend (terminal 1)
python main.py

# Execute frontend (terminal 2)
streamlit run frontend/streamlit_front.py
```

---

## 📁 Estrutura do Código

```
Assistente_Bancario/
│
├── 📂 agent/                    # Camada de Agentes
│   ├── agents.py               # Definição dos 4 agentes + Team
│   ├── constants.py            # Constantes (tokens, configs)
│   └── __init__.py
│
├── 📂 tools/                    # Ferramentas dos Agentes
│   ├── ferramentas_agentes.py  # Factories de tools por sessão
│   ├── tools.py                # Lógica de negócio (validação, score)
│   └── __init__.py
│
├── 📂 services/                 # Serviços de Infraestrutura
│   ├── clientes.py             # CRUD de clientes (CSV)
│   ├── websocket_manager.py    # Gerenciador de conexões WS
│   └── __init__.py             # Helpers (normalização, limites)
│
├── 📂 routes/                   # Rotas da API
│   └── chat_rotas.py           # Endpoint WebSocket /chat/ws
│
├── 📂 middlewares/              # Middlewares FastAPI
│   └── login_conexao.py        # Logging de conexões
│
├── 📂 frontend/                 # Interface de Usuário
│   └── streamlit_front.py      # Chat com tema bancário
│
├── 📂 data/                     # Dados Persistidos
│   ├── clientes.csv            # Base de clientes
│   ├── score_credito_base.csv  # Faixas de score/limite
│   ├── solicitacoes_*.csv      # Log de solicitações
│   └── agno_sessions.db        # Sessões do Agno (SQLite)
│
├── 📂 scripts/                  # Scripts Auxiliares
│   └── gerador_csv.py          # Gera dados iniciais
│
├── 📂 tests/                    # Testes Automatizados
│   ├── conftest.py             # Fixtures pytest
│   ├── test_agents.py          # Testes dos agentes
│   ├── test_api.py             # Testes da API
│   ├── test_tools.py           # Testes das ferramentas
│   └── test_streaming.py       # Testes de streaming
│
├── main.py                      # Entrypoint FastAPI
├── Dockerfile                   # Imagem Docker
├── docker-compose.yml           # Orquestração
├── docker-entrypoint.sh         # Script de inicialização
├── requirements.txt             # Dependências Python
├── .env.example                 # Exemplo de variáveis
└── README.md                    # Esta documentação
```

### Responsabilidades por Módulo

| Módulo | Responsabilidade |
|--------|------------------|
| `agent/` | Orquestração de agentes, instruções, roteamento |
| `tools/` | Lógica de negócio, validações, cálculos |
| `services/` | Acesso a dados, WebSocket, helpers |
| `routes/` | Endpoints HTTP/WebSocket |
| `frontend/` | Interface visual, tema, UX |
| `data/` | Persistência de estado e histórico |
| `tests/` | Garantia de qualidade |

---

## 🧪 Testes

### Executar Testes via Docker (Recomendado)

```bash
# Testes unitários (rápidos, sem dependência de API externa)
docker compose --profile test run --rm tests

# Testes de integração (requer GOOGLE_API_KEY, com delays para rate limit)
docker compose --profile test-integration run --rm tests-integration

# Todos os testes (unitários + integração)
docker compose --profile test-all run --rm tests-all
```

### Executar Testes Localmente

```bash
# Testes unitários
pytest tests/ -v -m "not integration"

# Todos os testes
pytest tests/ -v

# Com cobertura
pytest tests/ --cov=. --cov-report=html
```

### Estrutura de Testes

| Arquivo | Módulos Cobertos | Qtd Testes |
|---------|------------------|------------|
| `test_services.py` | `services/clientes.py`, `websocket_manager.py` | 18 |
| `test_ferramentas_agentes.py` | `tools/ferramentas_agentes.py` | 18 |
| `test_agents.py` | `agent/agents.py` (Team, agentes, sessão) | 14 |
| `test_tools.py` | `tools/tools.py` (validação, score, limite) | 7 |
| `test_middleware.py` | `middlwares/login_conexao.py` | 3 |
| `test_api.py` | `main.py`, `routes/chat_rotas.py` | 3 |
| `test_streaming.py` | WebSocket streaming E2E | 1 |

**Total: 71 testes (69 unitários + 2 de integração)**

### Cobertura por Camada

| Camada | Componentes Testados |
|--------|---------------------|
| **Services** | `limpar_cpf`, `normalizar_data`, `buscar_cliente_por_cpf`, `atualizar_limite_cliente`, `atualizar_score_cliente`, `obter_limite_permitido_por_score`, `registrar_solicitacao_limite`, `WebsocketManager` |
| **Tools** | `validando_cliente`, `consultando_limite`, `solicitacao_de_limite`, `atualizar_score_cliente` |
| **Ferramentas Agentes** | `registrar_cpf`, `registrar_data_nascimento`, `autenticar_cliente`, `verificar_autenticacao`, `consultar_limite_credito`, `solicitar_aumento_limite`, `atualizar_score_apos_entrevista`, `session_state` |
| **Agents** | `criar_agente_triagem`, `criar_agente_credito`, `criar_agente_entrevista`, `criar_agente_cambio`, `criar_time_banco_agil`, `get_team`, `limpar_sessao`, `processar_mensagem` |
| **Middleware** | `LoginConexaoMiddleware` (headers, tempo de processamento) |
| **API** | Rota home, conexão WebSocket, streaming |

### Exemplo de Teste

> **Nota:** Os testes utilizam um ambiente isolado em `tmp_path` com dados de teste específicos via fixtures, diferentes dos dados de demonstração em `data/clientes.csv`.

```python
# conftest.py - Fixture cria dados de teste isolados
@pytest.fixture
def csv_environment(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("AGNO_DATA_DIR", str(data_dir))
    # Popula CSVs com dados de teste
    pd.DataFrame([
        {"cpf": "12345678901", "nome": "Cliente Teste", ...}
    ]).to_csv(...)

# test_ferramentas_agentes.py - Testa ferramentas de sessão
def test_autenticar_sucesso(session_id, csv_environment):
    autenticar = criar_ferramenta_autenticacao(session_id)
    resultado = autenticar("12345678901", "13/02/1995")
    
    state = get_session_state(session_id)
    assert state["autenticado"] is True
    assert "SUCESSO" in resultado
```

### Testes de Integração

Os testes marcados com `@pytest.mark.integration` requerem a API do Gemini e incluem delays automáticos de 2 segundos entre chamadas para evitar rate limiting (429).

```python
@pytest.mark.skipif(not HAS_API_KEY, reason="Requer GOOGLE_API_KEY")
@pytest.mark.integration
def test_websocket_streaming_flow():
    # Testa fluxo completo com delays entre mensagens
    resposta = _send_and_collect(websocket, "Oi", delay=2)
    ...
```
---
## 👨‍💻 Autor

**Guilherme Fernandes**

[![GitHub](https://img.shields.io/badge/GitHub-GuilhermeFer29-black?logo=github)](https://github.com/GuilhermeFer29)

---

<div align="center">

**🏦 Banco Ágil - Seu banco digital, ágil e seguro!**

</div>
