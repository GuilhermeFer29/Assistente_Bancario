# Assistente Bancário V2 — Especificação de Design

**Data:** 2026-04-28
**Autor:** dev@iodo.digital + Claude
**Status:** Aprovado para implementação
**Projeto destino:** `/mnt/dados/Documentos/Assistente_Bancario/v2/` (subpasta do repo atual)
**Pacote Python:** `assistente_bancario_v2`

---

## 1. Objetivo

Construir um novo projeto (V2) que **une** as funcionalidades do `Assistente_Bancario` (atendimento bancário com 4 agentes: Triagem, Crédito, Entrevista de Score, Câmbio) com a **arquitetura técnica** do `BANKPER-AUTOMACAO` (split bot/gateway, autenticação por OTP via e-mail, Step-Up 2FA com página web, modelo de dados rico, fábrica padronizada de agentes Agno).

A V2 **não usa WhatsApp**. O canal é chat web (Streamlit + WebSocket).

## 2. Decisões fixas (brainstorming)

| Tema | Decisão |
|---|---|
| Tipo | Projeto novo do zero (não fork do Assistente nem do BANKPER) |
| Escopo | Domínio completo: auth OTP, limite, score, câmbio, saldo, contas a pagar/receber, transações, com 2FA nas operações sensíveis |
| Serviços | Split lógico, deploy unificado: `bot_service` + `banking_gateway` no mesmo repo. Comunicação `in_process` (dev) ou `http` (prod), por flag |
| Frontend | Streamlit (mantém estilo do `streamlit_app.py` atual) |
| Persistência | SQLite + SQLModel async (CSVs do V1 entram só como seed inicial) |
| Autenticação | Fluxo BANKPER puro: `cliente_id` + OTP por e-mail. **Sem CPF + data nasc.** |
| Step-Up 2FA | Operações sensíveis (aumento de limite, criar transação) passam por página web de confirmação com senha de transação (Argon2) |
| Modelo LLM | `Gemini(id="gemini-3-flash-preview", temperature=0.2)` |

## 3. Arquitetura geral

### 3.1 Estrutura de pastas

```
Assistente_Bancario_V2/
├── assistente_bancario_v2/
│   ├── bot_service/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/                 # config, logging, security, guardrails
│   │   │   ├── agents/               # agente_base + 7 agentes + team
│   │   │   ├── tools/                # gateway_tools.py
│   │   │   ├── services/             # gateway_client, email_client, websocket_manager
│   │   │   ├── routes/               # ws_chat, health
│   │   │   ├── schemas/
│   │   │   ├── db/                   # checkpointer (sessões Agno)
│   │   │   └── tests/
│   │   └── __init__.py
│   ├── banking_gateway/
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/                 # config, logging, security
│   │   │   ├── db/                   # models, database, seed
│   │   │   ├── domain/               # schemas Pydantic
│   │   │   ├── api/                  # rotas_clientes, otp, saldo, contas, transacao, confirmacao
│   │   │   ├── templates/            # confirmacao.html, sucesso.html, erro.html, expirado.html
│   │   │   ├── static/               # style.css
│   │   │   └── tests/
│   │   └── __init__.py
│   └── packages/
│       └── shared/                   # constants, schemas, utils
├── frontend/
│   └── streamlit_app.py
├── data/                              # *.db gerados (gitignored)
├── infra/
│   ├── docker-compose.yml             # bot + gateway + mailpit + streamlit
│   ├── Dockerfile.bot
│   ├── Dockerfile.gateway
│   └── Dockerfile.streamlit
├── docs/
│   └── superpowers/specs/
├── scripts/
│   ├── run_dev.sh
│   └── seed_data.py
├── pyproject.toml
├── requirements.txt
├── .env.example
├── .gitignore
├── pytest.ini
└── README.md
```

### 3.2 Comunicação bot → gateway

`bot_service/app/services/gateway_client.py` define um `Protocol` único e duas implementações:

- `InProcessGatewayClient` — importa funções/repositórios do gateway diretamente. Usado em dev e em testes (default).
- `HttpGatewayClient` — usa `httpx.AsyncClient` apontando para `GATEWAY_URL`. Usado quando `GATEWAY_TRANSPORT=http`.

A escolha é por flag em `Settings`. Os agentes nunca conhecem qual transporte está ativo.

## 4. Time de agentes

Mantém o **padrão passthrough** do Agno v2.x (`respond_directly=True`, `determine_input_for_members=False`). Team Leader apenas roteia, membro responde direto ao usuário.

Todos os agentes são criados pela fábrica `criar_agente()` em `agents/agente_base.py` (vinda do BANKPER), garantindo configuração comum: modelo Gemini, `markdown=True`, `add_history_to_context=True`, `num_history_runs=10`, `enable_session_summaries=True`, sessão SQLite.

| Agente | Papel | Tools |
|---|---|---|
| **Triagem** | Identifica `cliente_id`, dispara/valida OTP por e-mail | `iniciar_login`, `validar_otp`, `verificar_auth` |
| **Saldo** | Consulta saldo disponível e bloqueado | `obter_saldo_cliente` |
| **Contas** | Lista contas a pagar/receber/vencidas/pagas | `obter_contas_cliente(tipo, periodo)` |
| **Transacoes** | Cria transação (a_pagar/a_receber) com 2FA via página web | `criar_transacao_pendente`, `gerar_link_confirmacao` |
| **Credito** | Consulta limite e solicita aumento (sensível → 2FA) | `consultar_limite`, `solicitar_aumento_limite` |
| **Entrevista** | 5 perguntas → atualiza score | `atualizar_score_apos_entrevista` |
| **Cambio** | Cotações de moedas estrangeiras | `TavilyTools()` |

### 4.1 Roteamento (Team Leader)

Prioridade:

1. Se um agente está **no meio de um fluxo** (ex: Triagem esperando OTP, Entrevista esperando resposta) → mesmo agente.
2. Se cliente **não autenticado** → Triagem.
3. Por palavras-chave:
   - "saldo", "extrato" → Saldo
   - "conta", "pagar", "receber", "vencida", "vencimento" → Contas
   - "transferir", "criar transação", "novo pagamento" → Transacoes
   - "limite", "crédito", "aumento" → Credito
   - "score", "entrevista", "pontuação" → Entrevista
   - "cotação", "dólar", "euro", "câmbio", "moeda" → Cambio
4. Dúvida → Triagem.

### 4.2 Sessão e memória

- `session_id` por aba do Streamlit (`uuid4()` em `st.session_state`).
- `user_id` Agno = `cliente_id` autenticado (isola memórias por cliente).
- Cache de `Team` por `session_id` em memória do `bot_service` (`_team_cache`).
- Persistência via `agno.db.sqlite.SqliteDb` em `data/bot.db`.
- `enable_user_memories=True`, `share_member_interactions=True`.

## 5. Modelo de dados

### 5.1 Banco do Gateway (`data/gateway.db`)

| Tabela | Campos principais |
|---|---|
| `clientes` | `id_cliente` (unique), `nome`, `email`, `telefone`, `dt_nascimento`, `cpf` (legado V1, não usado em auth), `score_credito`, `renda_mensal`, `limite_credito`, `confiavel`, `ativo`, `senha_hash` (Argon2 — confirmação web) |
| `saldos` | `id_cliente` (FK), `saldo_disponivel`, `saldo_bloqueado`, `atualizado_em` |
| `contas` | `id_conta`, `id_cliente`, `descricao`, `valor`, `data_vencimento`, `status` (PENDENTE/PAGA/CANCELADA), `tipo` (a_pagar/a_receber), `nome_pagador?`, `data_prevista?` |
| `transacoes` | `id_requisicao`, `id_cliente`, `chave_idempotencia` (unique), `tipo`, `valor`, `data_vencimento`, `status` (PENDENTE/CONFIRMADA/REJEITADA/DUPLICADA), `criado_em` |
| `solicitacoes_limite` | `id_cliente` (FK), `data_hora_solicitacao`, `limite_atual`, `novo_limite_solicitado`, `status_pedido` |
| `score_credito_base` | `score_min`, `score_max`, `limite_maximo` |
| `confirmacoes_pendentes` | `token` (UUID hex), `id_cliente`, `dados_transacao_json`, `status`, `tentativas_senha`, `expira_em` |
| `otps` | `id`, `id_cliente`, `codigo_hash` (Argon2), `criado_em`, `expira_em`, `tentativas`, `consumido`, `bloqueado_ate?` |

### 5.2 Banco do Bot (`data/bot.db`)

Gerenciado pelo Agno: tabelas internas de sessões, histórico, summaries, memórias.

### 5.3 Seed inicial

`banking_gateway/app/db/seed.py`, executado no startup:

- Importa `clientes.csv` e `score_credito_base.csv` do V1 (se existirem em `data/seed/`), populando `clientes` e `score_credito_base`.
- Para cada cliente importado, cria `saldos` com valor inicial (R$ 5.000–10.000 aleatórios) e contas a pagar/receber de exemplo (mínimo 3 cada).
- Idempotente: se cliente já existe, pula.
- Após seed inicial, CSVs viram apenas histórico — toda leitura/escrita ocorre no SQLite.

## 6. Autenticação e Step-Up 2FA

### 6.1 Login (Triagem + OTP)

```
Cliente → Streamlit → bot_service WS → Triagem
  1. Triagem: "Olá! Informe seu ID de cliente (ex: CLI001)."
  2. Cliente: "CLI001"
  3. Tool iniciar_login("CLI001"):
     - Gateway: busca cliente, gera OTP de 6 dígitos
     - Salva codigo_hash (Argon2) + expiracao 5min em otps
     - email_client envia OTP via SMTP (Mailpit em dev)
  4. Triagem: "Enviei um código para seu e-mail. Digite-o aqui."
  5. Cliente: "123456"
  6. Tool validar_otp("123456"):
     - Confere hash, expiração, tentativas (máx 3)
     - Sucesso → marca cliente_id autenticado na sessão
  7. Triagem: menu de opções.
```

**Bloqueio:** após 3 tentativas erradas, `cliente_id` fica bloqueado por 15 minutos (`bloqueado_ate`).

### 6.2 Step-Up para operações sensíveis

Operações marcadas como sensíveis: **aumento de limite**, **criar transação a pagar**, **criar transação a receber**.

```
Agente (Credito ou Transacoes) → Gateway: criar_confirmacao_pendente(payload)
  → Gateway: cria token UUID, salva confirmacoes_pendentes (expira 10min)
  → Devolve URL: http://localhost:8001/confirmar/{token}

Agente → Cliente (chat): "Para concluir, abra: {url} e digite sua senha."
Streamlit detecta URL e renderiza botão "🔒 Abrir confirmação".

Cliente → Página HTML (Jinja, no gateway):
  - Mostra descrição, valor, vencimento.
  - Campo de senha + botão Confirmar.

POST /confirmar/{token}:
  - Valida senha_hash (Argon2) do cliente.
  - Sucesso: executa operação real (ex: insere transacao, atualiza limite_credito).
  - Marca confirmacao CONFIRMADA.
  - Tela de sucesso com link "Voltar ao chat".
```

**Tentativas:** 3 por token. Após esgotar, marca `REJEITADA`.

## 7. Frontend (Streamlit)

### 7.1 `frontend/streamlit_app.py`

- Mantém visual e fluxo do `streamlit_app.py` do V1 (chat, histórico, indicador de digitação, sidebar com botão "Nova Conversa").
- Conecta via WebSocket a `ws://localhost:8000/chat/ws/{session_id}`.
- `session_id` em `st.session_state["session_id"]` (uma sessão por aba).
- Renderiza Markdown completo (tabelas, listas, negrito).
- **Detecção de link de confirmação:** regex `/confirmar/[a-f0-9-]+` no texto da resposta — quando casa, exibe botão "🔒 Abrir confirmação" abrindo em nova aba (`webbrowser.open` ou link Markdown com `target="_blank"`).

### 7.2 Transporte WS no `bot_service`

- `routes/ws_chat.py` — `WebSocket /chat/ws/{session_id}`.
- `services/websocket_manager.py` — adaptado do V1: `conexao()`, `enviar_mensagem()`, `desconexao()`.
- `STREAM_END_TOKEN = "<<END_OF_STREAM>>"` para sinalizar fim de mensagem.
- Streaming Agno desativado por padrão (flag `STREAM_ENABLED=false`), resposta completa de uma vez.

### 7.3 Página de confirmação (Gateway)

- `banking_gateway/app/templates/confirmacao.html` — Jinja2: descrição da operação, valor (formatado R$), data, campo password, botão Confirmar.
- `banking_gateway/app/static/style.css` — estilo enxuto, responsivo, sem dependências externas.
- Telas de pós: `sucesso.html`, `erro.html`, `expirado.html`.

## 8. Stack técnica

### 8.1 Versões fixadas

```
agno==2.5.3
fastapi==0.131.0
uvicorn[standard]==0.41.0
sqlmodel==0.0.34
aiosqlite==0.22.1
pydantic==2.12.5
pydantic-settings==2.13.1
httpx==0.28.1
argon2-cffi==25.1.0
slowapi==0.1.9
aiosmtplib==3.0.2
Jinja2==3.1.6
structlog==25.5.0
google-genai==1.64.0
tavily-python
streamlit==1.51.0
websockets==14.2
pytest==9.0.2
pytest-asyncio==1.3.0
pytest-cov==7.0.0
ruff==0.15.2
mypy==1.19.1
pre-commit==4.0.1
```

### 8.2 Configuração (`pydantic-settings`)

Variáveis principais (em `.env`):

```
# LLM
GEMINI_API_KEY=
TAVILY_API_KEY=
GEMINI_MODEL=gemini-3-flash-preview

# Transporte
GATEWAY_TRANSPORT=in_process     # in_process | http
GATEWAY_URL=http://localhost:8001

# E-mail (Mailpit em dev)
SMTP_HOST=mailpit
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=no-reply@bancoagil.local

# Banco de dados
BOT_DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
GATEWAY_DATABASE_URL=sqlite+aiosqlite:///./data/gateway.db

# Segurança / Tempos
OTP_EXPIRACAO_MIN=5
OTP_MAX_TENTATIVAS=3
OTP_BLOQUEIO_MIN=15
CONFIRMACAO_EXPIRACAO_MIN=10
CONFIRMACAO_MAX_TENTATIVAS=3

# App
STREAM_ENABLED=false
LOG_LEVEL=INFO
DEBUG=false
```

### 8.3 Logging e observabilidade

- `structlog` JSON em ambos os serviços.
- `correlation_id` injetado por mensagem WS / requisição HTTP via middleware.
- Eventos-chave: `login_iniciado`, `otp_enviado`, `otp_validado`, `otp_rejeitado`, `cliente_bloqueado`, `confirmacao_criada`, `confirmacao_validada`, `transacao_criada`, `limite_atualizado`.

### 8.4 Segurança

- Argon2id para `senha_hash` e `codigo_hash` de OTP.
- `slowapi` rate-limit nas rotas `/otp/iniciar`, `/otp/validar`, `/confirmar/{token}` (POST): 5/min por IP.
- Validação Pydantic em todas as entradas.
- Sem segredos em código. `.env` no `.gitignore`.

### 8.5 Testes

| Camada | Tipo | Arquivos exemplares |
|---|---|---|
| Gateway | unit + integração | `test_otp.py`, `test_saldo.py`, `test_contas.py`, `test_transacao_idempotencia.py`, `test_confirmacao_step_up.py`, `test_seed_csv.py` |
| Bot | unit + integração | `test_agente_triagem_otp.py`, `test_team_routing.py`, `test_gateway_client_inprocess.py`, `test_gateway_client_http.py`, `test_ws_chat.py`, `test_step_up_flow.py` |
| E2E | pytest + httpx | `test_e2e_login_otp.py`, `test_e2e_aumento_limite_2fa.py`, `test_e2e_criar_transacao_2fa.py` |
| Frontend | smoke manual + opcional Playwright | smoke do chat |

**Meta:** ≥ 80% de cobertura combinada (`pytest-cov`).

### 8.6 Lint, type-check, formatação

- `ruff` (lint + formatter), config `pyproject.toml` herdada do BANKPER.
- `mypy --strict` em `bot_service`, `banking_gateway`, `packages`.
- `pre-commit` opcional.

### 8.7 Docker

`infra/docker-compose.yml` com 4 serviços:

- `gateway` — `Dockerfile.gateway`, porta 8001.
- `bot` — `Dockerfile.bot`, porta 8000, depende de `gateway` e `mailpit`.
- `mailpit` — `axllent/mailpit:latest`, SMTP 1025 / UI 8025.
- `streamlit` — `Dockerfile.streamlit`, porta 8501, depende de `bot`.

Volumes para `data/*.db`. Sem Postgres, Redis ou Evolution API.

## 9. Plano de execução (8 fases)

| # | Fase | Entrega-chave | Critério de saída |
|---|---|---|---|
| 1 | Esqueleto e tooling | Estrutura, configs, healthchecks, docker-compose | `/health` 200 em ambos, `pytest` roda |
| 2 | Banking Gateway base | Models, seed, rotas clientes/saldo/contas | Endpoints retornam dados de seed |
| 3 | Tools + gateway_client | Protocol + 2 implementações (in-process/http) | Mesmo contrato em testes paralelos |
| 4 | Triagem + OTP por e-mail | OTP rotas, email_client, agente_base, ws_chat, Streamlit | Login completo via OTP no Streamlit |
| 5 | Agentes informativos | Agentes Saldo, Contas, Cambio | Consultas funcionam autenticado |
| 6 | Crédito + Entrevista | Migração da lógica de score/limite, agentes Credito/Entrevista | Consulta + entrevista E2E |
| 7 | Step-Up 2FA + Transações | Confirmações pendentes, página HTML, agente Transacoes, aumento de limite | Step-up completo via web |
| 8 | Polimento | Rate-limit, structlog, coverage, README | `pytest --cov` ≥ 80%, lint/type limpos |

**Estimativa total:** ~14 dias úteis.

## 10. Não-objetivos (escopo explicitamente fora)

- Integração com WhatsApp ou qualquer canal externo de mensageria.
- Postgres / Redis / Evolution API.
- Banco real ou integração com 3rd party financeiro.
- Multi-tenant ou multi-instância.
- App mobile.
- Internacionalização (todo conteúdo em PT-BR).
- Pipeline CI/CD (fica para versão posterior).

## 11. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Compatibilidade Agno 2.3 (V1) → 2.5 (V2) | Releitura dos agentes, validação por testes em cada agente migrado |
| OTP por e-mail demora ou falha em dev | Mailpit como SMTP local; fallback de log em DEBUG mostra OTP no console |
| `in_process` e `http` divergirem em comportamento | Suite de testes paralela rodando contra as duas implementações com mesmo contrato |
| Streamlit + WebSocket + threads | Manter `stream=False` por padrão; `websocket-client` síncrono num event loop dedicado por aba |
| Migração CSV → SQLite com perda de dados | Seed idempotente, snapshot em `data/seed/` antes do startup |

## 12. Referências

- `Assistente_Bancario` (V1) — `/mnt/dados/Documentos/Assistente_Bancario/`
- `BANKPER-AUTOMACAO` — `/home/guilhermedev/Documentos/IODO PROJETOS/BANKPER-AUTOMACAO/`
- Docs Agno v2.x — passthrough team pattern, session summaries, user memories
