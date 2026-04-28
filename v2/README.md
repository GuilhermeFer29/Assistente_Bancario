# Assistente Bancário V2

**Chat bancário web** com 7 agentes Agno, autenticação por **OTP por e-mail** e **Step-Up 2FA via página web** para operações sensíveis. Sem WhatsApp.

> Spec completa em [docs/superpowers/specs/](docs/superpowers/specs/) · Plano de execução em [docs/superpowers/plans/](docs/superpowers/plans/)

---

## Arquitetura

```
[ Streamlit :8501 ]
        │  WebSocket
        ▼
[ bot_service :8000 ] ── 7 agentes Agno (Triagem, Saldo, Contas, Transacoes,
        │                                 Credito, Entrevista, Cambio)
        │  in_process | http
        ▼
[ banking_gateway :8001 ] ──► SQLite (gateway.db)
        │
        ▼
[ mailpit :1025/8025 ] (SMTP dev)
```

**bot_service**: orquestração dos agentes via `Team Agno` (passthrough), WebSocket de chat, sessão isolada por `session_id`, memórias por `cliente_id` autenticado.

**banking_gateway**: REST com clientes, saldo, contas a pagar/receber, transações com idempotência, faixas de score, OTP, confirmações pendentes (Step-Up). Renderiza página HTML de confirmação 2FA.

**packages/shared**: constantes, schemas e utilitários comuns.

---

## Agentes

| Agente | Papel | Ferramentas |
|---|---|---|
| **Triagem** | Login: ID + OTP por e-mail | `iniciar_login`, `validar_otp`, `verificar_auth` |
| **Saldo** | Saldo disponível e bloqueado | `obter_saldo` |
| **Contas** | A pagar / a receber / vencidas / pagas | `listar_contas(tipo)` |
| **Transacoes** | Cria transação com **Step-Up 2FA** | `iniciar_transacao(...)` |
| **Credito** | Limite + aumento via Step-Up | `consultar_limite`, `solicitar_aumento_limite` |
| **Entrevista** | 5 perguntas → score | `atualizar_score_apos_entrevista` |
| **Cambio** | Cotações via Tavily | `TavilyTools()` |

---

## Quickstart (local)

```bash
cd v2
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# editar .env: GEMINI_API_KEY, TAVILY_API_KEY (opcional)
```

**Subir os 3 serviços:**

```bash
# Terminal 1 — gateway
PYTHONPATH=. uvicorn assistente_bancario_v2.banking_gateway.app.main:app --port 8001 --reload

# Terminal 2 — bot
PYTHONPATH=. uvicorn assistente_bancario_v2.bot_service.app.main:app --port 8000 --reload

# Terminal 3 — frontend
streamlit run frontend/streamlit_app.py
```

ou com o helper:

```bash
./scripts/run_dev.sh start
./scripts/run_dev.sh logs
./scripts/run_dev.sh stop
```

**URLs:**
- Chat (Streamlit): http://localhost:8501
- Bot OpenAPI: http://localhost:8000/docs
- Gateway OpenAPI: http://localhost:8001/docs

## Quickstart (Docker — recomendado)

Tudo lê de `.env`. Sem hardcode.

```bash
cd v2
make env            # cria .env a partir de .env.example
# editar .env: GEMINI_API_KEY (e TAVILY_API_KEY se quiser câmbio)

make build          # builda as 3 imagens
make up             # sobe gateway + bot + streamlit + mailpit
make logs           # acompanha logs
make ps             # status dos serviços
make down           # derruba (mantém volumes)
make down-clean     # derruba e apaga volumes
```

URLs (host):
- Streamlit:    `http://localhost:${STREAMLIT_PORT:-8501}`
- Bot OpenAPI:  `http://localhost:${BOT_PORT:-8000}/docs`
- Gateway API:  `http://localhost:${GATEWAY_PORT:-8001}/docs`
- Mailpit UI:   `http://localhost:${MAILPIT_UI_PORT:-8025}`

Volumes persistentes: `assistente-v2-gateway-data` (gateway.db) e `assistente-v2-bot-data` (bot.db).

**Detalhes:**
- Imagens self-contained (código baked, não usa volume mount de fonte).
- Usuário não-root dentro do container.
- Healthchecks em todos os serviços (`depends_on: condition: service_healthy`).
- `apt-get upgrade` aplica patches de segurança no build.
- Mailpit recebe os OTPs em dev (`SMTP_HOST=mailpit` no compose).

---

## Fluxos principais

### 1. Login (OTP por e-mail)

1. Cliente: "olá"
2. Triagem: pede o ID (ex `CLI001`)
3. Cliente: `CLI001`
4. Triagem chama `iniciar_login` → gateway gera OTP, envia e-mail
5. Triagem: "código enviado, digite-o"
6. Cliente: `123456`
7. Triagem chama `validar_otp` → gateway confere hash Argon2
8. Triagem: dá boas-vindas e oferece menu

### 2. Aumento de limite (Step-Up)

1. Credito chama `solicitar_aumento_limite(novo_limite)`
2. Gateway verifica faixa de score:
   - **Acima da faixa** → rejeita imediatamente
   - **Dentro da faixa** → cria `confirmacoes_pendentes` (token UUID, expira em 10min)
3. Gateway devolve URL `/confirmar/{token}`
4. Streamlit detecta a URL no texto da resposta e renderiza botão **🔒 Abrir confirmação**
5. Cliente abre página HTML do gateway → digita senha de transação → gateway valida (Argon2) → atualiza limite e marca CONFIRMADA
6. Tela de sucesso

### 3. Criar transação a pagar/receber

Mesmo fluxo de Step-Up, mas executando insert na tabela `transacoes` com idempotência por `chave_idempotencia`.

### 4. Entrevista de score

1. Entrevista pergunta uma de cada vez: renda, emprego, despesas, dependentes, dívidas
2. Ao final, chama `atualizar_score_apos_entrevista(...)` com a fórmula:

   ```
   score = (renda / (despesas + 1)) * 30
         + peso_emprego[formal=300, autonomo=200, desempregado=0]
         + peso_dependentes[0=100, 1=80, 2=60, 3+=30]
         + peso_dividas[sim=-100, nao=100]
   ```

   limitado a `[0, 1000]`.

---

## Variáveis de ambiente principais

| Var | Default | Função |
|---|---|---|
| `GEMINI_API_KEY` | — | Chave do Gemini (obrigatória para os agentes) |
| `TAVILY_API_KEY` | — | Chave da Tavily (opcional, para Câmbio) |
| `GATEWAY_TRANSPORT` | `in_process` | `in_process` (dev) ou `http` (prod) |
| `GATEWAY_URL` | `http://localhost:8001` | URL do gateway quando `http` |
| `SMTP_HOST` | `mailpit` | Host SMTP |
| `SMTP_PORT` | `1025` | Porta SMTP |
| `OTP_EXPIRACAO_MIN` | `5` | Expiração do OTP |
| `OTP_MAX_TENTATIVAS` | `3` | Tentativas antes de bloquear |
| `CONFIRMACAO_EXPIRACAO_MIN` | `10` | Expiração do token de Step-Up |
| `DEBUG` | `false` | Em `true`, OTP/email vão para o log |

---

## Testes

```bash
PYTHONPATH=. pytest -v
PYTHONPATH=. pytest --cov=assistente_bancario_v2 --cov-report=term-missing
```

26 testes cobrindo:
- Healthchecks bot + gateway
- Seed idempotente
- Endpoints clientes/saldo/contas
- Fluxo OTP completo (sucesso, código incorreto, bloqueio)
- Limite + aumento (faixa + step-up)
- Atualização de score
- Página HTML de confirmação (renderiza, senha errada, senha correta)
- `gateway_client` in_process

---

## Estrutura

```
v2/
├── assistente_bancario_v2/
│   ├── bot_service/app/
│   │   ├── core/              # config, logging
│   │   ├── agents/            # agente_base + 7 agentes + team
│   │   ├── tools/             # auth_tools, gateway_tools
│   │   ├── services/          # gateway_client (Protocol + 2 impls), websocket_manager, sessao_estado
│   │   ├── routes/            # ws_chat
│   │   └── tests/
│   ├── banking_gateway/app/
│   │   ├── core/              # config, logging, rate_limit
│   │   ├── db/                # models (8 tabelas), database, repositorio, seed
│   │   ├── domain/            # schemas Pydantic
│   │   ├── api/               # rotas_clientes, saldo, contas, otp, credito, transacao, confirmacao
│   │   ├── services/          # email_client, otp_service, credito_service, transacao_service, confirmacao_service
│   │   ├── templates/         # confirmacao.html, sucesso.html, erro.html, expirado.html
│   │   ├── static/            # style.css
│   │   └── tests/
│   └── packages/shared/       # constants, schemas, utils
├── frontend/streamlit_app.py
├── data/seed/                 # CSVs do V1 (clientes, score base)
├── infra/                     # docker-compose + Dockerfiles
├── scripts/run_dev.sh
└── docs/superpowers/{specs,plans}/
```

---

## Próximos passos sugeridos

- Adicionar Playwright para smoke E2E do Streamlit.
- Migrar SQLite → Postgres para concorrência real em produção.
- Senha de transação por cliente (hoje todos usam `1234` no seed dev).
- Métricas Prometheus + dashboard.
- Sandbox de "agência física" como segundo canal.
