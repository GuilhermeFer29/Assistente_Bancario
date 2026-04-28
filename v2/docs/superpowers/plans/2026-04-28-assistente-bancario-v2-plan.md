# Assistente Bancário V2 — Plano de Implementação

> **Para workers agentic:** SUB-SKILL OBRIGATÓRIA: Use superpowers:subagent-driven-development (recomendado) ou superpowers:executing-plans para implementar este plano tarefa-a-tarefa. Os passos usam sintaxe de checkbox (`- [ ]`) para tracking.

**Goal:** Construir o `assistente_bancario_v2/` (split bot/gateway, OTP por e-mail, 7 agentes Agno, Step-Up 2FA via web) dentro de `/mnt/dados/Documentos/Assistente_Bancario/v2/`, em 8 fases TDD.

**Architecture:** Split lógico (bot_service + banking_gateway) no mesmo repo, transporte in-process (dev) ou HTTP (prod) via flag. Streamlit como frontend com WebSocket. SQLite + SQLModel async. Agno 2.5.3 com Gemini.

**Tech Stack:** Python 3.11, FastAPI 0.131, Agno 2.5.3, Gemini 3 Flash Preview, SQLModel 0.0.34, aiosqlite, Streamlit 1.51, structlog, argon2, slowapi, aiosmtplib, Mailpit (dev SMTP), pytest 9.

**Spec:** `docs/superpowers/specs/2026-04-28-assistente-bancario-v2-design.md`

---

## Estrutura final esperada

```
v2/
├── assistente_bancario_v2/
│   ├── bot_service/app/{core,agents,tools,services,routes,schemas,db,tests}
│   ├── banking_gateway/app/{core,db,domain,api,templates,static,tests}
│   └── packages/shared/
├── frontend/streamlit_app.py
├── data/{bot.db,gateway.db,seed/}
├── infra/{docker-compose.yml,Dockerfile.{bot,gateway,streamlit}}
├── scripts/{run_dev.sh,seed_data.py}
├── docs/superpowers/{specs,plans}/
├── pyproject.toml, requirements.txt, .env.example, .gitignore, pytest.ini, README.md
```

---

## Fase 1 — Esqueleto + Tooling

**Saída:** `pytest` roda 0 testes, `/health` retorna 200 em ambos os serviços, `docker compose up` sobe sem erro.

### Task 1.1: Pyproject, requirements, .env.example, .gitignore

**Files (todos em `v2/`):**
- Create: `pyproject.toml`, `requirements.txt`, `.env.example`, `.gitignore`, `pytest.ini`, `README.md`

- [ ] Criar `requirements.txt` com versões fixadas conforme spec §8.1
- [ ] Criar `pyproject.toml` (ruff + mypy + pytest configs do BANKPER, ajustar `src` para `assistente_bancario_v2`)
- [ ] Criar `.env.example` com todas as variáveis da spec §8.2
- [ ] Criar `.gitignore` (Python padrão + `data/*.db` + `.venv` + `.env`)
- [ ] Criar `pytest.ini` (`asyncio_mode=auto`, testpaths)
- [ ] Criar `README.md` (quickstart resumido)

### Task 1.2: Pacotes Python e __init__.py

- [ ] `touch` em todos os `__init__.py` necessários (bot_service, banking_gateway, packages.shared, e em todos os subpacotes `app/*`)

### Task 1.3: shared/constants.py + utils.py + schemas.py

**Files:**
- Create: `assistente_bancario_v2/packages/shared/{constants.py,utils.py,schemas.py}`

- [ ] `constants.py`: `StatusConta`, `TipoTransacao`, `StatusTransacao`, `STREAM_END_TOKEN`
- [ ] `utils.py`: `gerar_id_correlacao()`, `formatar_brl(valor)`, `agora_utc()`
- [ ] `schemas.py`: `EventoEntrada` (mensagem WS), `RespostaPadrao`

### Task 1.4: Configs (pydantic-settings) e logging

**Files:**
- Create: `bot_service/app/core/{config.py,logging_config.py}`
- Create: `banking_gateway/app/core/{config.py,logging_config.py}`

- [ ] `bot_service/app/core/config.py`: classe `ConfiguracaoBot(BaseSettings)` com todos os env vars do bot
- [ ] `banking_gateway/app/core/config.py`: classe `ConfiguracaoGateway(BaseSettings)` com env vars do gateway
- [ ] `logging_config.py` (idêntico em ambos): structlog JSON + `correlation_id` contextvar

### Task 1.5: main.py mínimo dos dois serviços

**Files:**
- Create: `bot_service/app/main.py`, `banking_gateway/app/main.py`

- [ ] `banking_gateway/app/main.py`: FastAPI com `GET /health` retornando `{"status":"ok","servico":"banking_gateway"}`
- [ ] `bot_service/app/main.py`: FastAPI com `GET /health` retornando `{"status":"ok","servico":"bot_service"}`
- [ ] Lifecycle (startup/shutdown) com `configurar_logging`

**Teste:**
```python
# bot_service/app/tests/test_health.py
from fastapi.testclient import TestClient
from assistente_bancario_v2.bot_service.app.main import app

def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "servico": "bot_service"}
```
- [ ] Idem em `banking_gateway/app/tests/test_health.py`
- [ ] `pytest -v` ambos passam

### Task 1.6: Docker Compose + Dockerfiles

**Files:**
- Create: `infra/{docker-compose.yml,Dockerfile.bot,Dockerfile.gateway,Dockerfile.streamlit}`
- Create: `scripts/run_dev.sh`

- [ ] `Dockerfile.bot`: Python 3.11-slim, `pip install -r requirements.txt`, `CMD uvicorn assistente_bancario_v2.bot_service.app.main:app --host 0.0.0.0 --port 8000`
- [ ] `Dockerfile.gateway`: idem para gateway na 8001
- [ ] `Dockerfile.streamlit`: Python 3.11-slim, `CMD streamlit run frontend/streamlit_app.py --server.port=8501`
- [ ] `docker-compose.yml`: 4 serviços (bot, gateway, mailpit, streamlit) + volumes
- [ ] `scripts/run_dev.sh`: roda os 3 serviços localmente em background com `uvicorn` e `streamlit`
- [ ] **Commit Phase 1:** `feat: V2 phase 1 - skeleton, tooling, healthchecks`

---

## Fase 2 — Banking Gateway base

**Saída:** Endpoints `/clientes/{id}`, `/saldo/{id}`, `/contas/{id}?tipo=...` retornam dados de seed importado dos CSVs do V1.

### Task 2.1: SQLModel models

**Files:**
- Create: `banking_gateway/app/db/{models.py,database.py,seed.py}`

- [ ] `models.py`: `Cliente`, `Saldo`, `Conta`, `Transacao`, `SolicitacaoLimite`, `ScoreCreditoBase`, `ConfirmacaoPendente`, `Otp` (campos conforme spec §5.1)
- [ ] `database.py`: `engine` async + `fabrica_sessao()` + `inicializar_banco()` (cria tabelas)
- [ ] Teste: `test_models.py` cria cliente, salva, recupera

### Task 2.2: Seed importando CSVs V1

- [ ] Copiar CSVs de `/mnt/dados/Documentos/Assistente_Bancario/data/*.csv` para `v2/data/seed/`
- [ ] `seed.py::executar_seed(sessao)`: idempotente, importa `clientes.csv` e `score_credito_base.csv`, popula saldo aleatório (5–10k) e 3 contas a_pagar + 3 a_receber por cliente
- [ ] Teste: `test_seed.py` verifica idempotência (rodar 2× resulta no mesmo número de registros)

### Task 2.3: Schemas Pydantic

**Files:**
- Create: `banking_gateway/app/domain/schemas.py`

- [ ] `RespostaCliente`, `RespostaSaldo`, `RespostaConta`, `RespostaListaContas`, `RespostaTransacao`, `RequisicaoTransacao`, `RespostaConfirmacao`, `RequisicaoOtpIniciar`, `RequisicaoOtpValidar` (conforme BANKPER + adaptações)

### Task 2.4: Rotas /clientes, /saldo, /contas

**Files:**
- Create: `banking_gateway/app/api/{rotas_clientes.py,rotas_saldo.py,rotas_contas.py}`

- [ ] `GET /clientes/{id_cliente}` → `RespostaCliente`
- [ ] `GET /saldo/{id_cliente}` → `RespostaSaldo`
- [ ] `GET /contas/{id_cliente}?tipo=a_vencer|vencidas|pagas&data_inicio&data_fim` → `RespostaListaContas`
- [ ] Registrar routers em `main.py`
- [ ] Lifespan executa `inicializar_banco()` + `executar_seed()`
- [ ] Testes integração com `httpx.AsyncClient` para cada endpoint
- [ ] **Commit Phase 2:** `feat: V2 phase 2 - gateway base (models, seed, rotas clientes/saldo/contas)`

---

## Fase 3 — Tools + gateway_client (in-process | http)

### Task 3.1: Protocol GatewayClient

**Files:**
- Create: `bot_service/app/services/gateway_client.py`

- [ ] `Protocol GatewayClient` com métodos: `obter_cliente`, `consultar_saldo`, `consultar_contas`, `criar_otp`, `validar_otp`, `criar_confirmacao`, `consultar_limite`, `solicitar_aumento_limite`, `atualizar_score`, `criar_transacao`, etc.

### Task 3.2: InProcessGatewayClient

- [ ] Implementação que importa funções/repositórios do gateway diretamente (mesma sessão SQLAlchemy via dependência injetada). Útil em testes e dev.

### Task 3.3: HttpGatewayClient

- [ ] Implementação com `httpx.AsyncClient`, base URL = `GATEWAY_URL`. Reutiliza client global, fechamento no shutdown.

### Task 3.4: Factory

- [ ] `criar_gateway_client(config)` retorna a impl correta baseada em `GATEWAY_TRANSPORT`.
- [ ] Testes paralelos: para cada método, mesmo input → mesmo output em ambas implementações (parametrize).
- [ ] **Commit Phase 3:** `feat: V2 phase 3 - gateway_client (Protocol + in_process + http)`

---

## Fase 4 — Triagem + OTP por e-mail

### Task 4.1: Tabela e rotas OTP

- [ ] `Otp` model já existe (Fase 2). Adicionar regras em service: `criar_otp(id_cliente)` (gera código 6 dígitos, hash Argon2, expira em 5min, salva), `validar_otp(id_cliente, codigo)` (confere hash, tentativas, bloqueio).
- [ ] `POST /otp/iniciar` body `{id_cliente}` → envia e-mail + retorna `{enviado: true, expira_em: ...}` (nunca devolve o código)
- [ ] `POST /otp/validar` body `{id_cliente, codigo}` → `{valido: bool, motivo?: str}`
- [ ] Rate limit 5/min por IP nas duas rotas (slowapi)
- [ ] Testes: ok, código errado, expirado, bloqueio após 3 tentativas

### Task 4.2: email_client.py

**Files:**
- Create: `bot_service/app/services/email_client.py`
- Create: `banking_gateway/app/services/email_client.py` (gateway envia o OTP)

- [ ] aiosmtplib + Jinja2 template `otp.html` simples
- [ ] Em `DEBUG=true`, log do OTP no console (fallback se Mailpit não estiver up)

### Task 4.3: agente_base.py (fábrica)

**Files:**
- Create: `bot_service/app/agents/agente_base.py`

- [ ] Função `criar_agente(nome, role, descricao, instrucoes, tools)` retornando `Agent` Agno padronizado: Gemini, markdown, history, session summaries, sqlite db `data/bot.db`
- [ ] Retorna `None` se `GEMINI_API_KEY` ausente (fallback)

### Task 4.4: agente_triagem.py

**Files:**
- Create: `bot_service/app/agents/agente_triagem.py`
- Create: `bot_service/app/tools/auth_tools.py`

- [ ] Tools: `iniciar_login(cliente_id)`, `validar_otp(codigo)`, `verificar_auth()` (estado em memória keyed por session_id)
- [ ] Agente Triagem com instruções claras (PT-BR, fluxo: pede ID, dispara OTP, valida)

### Task 4.5: Team mínimo + WebSocket + Streamlit

**Files:**
- Create: `bot_service/app/agents/team.py`
- Create: `bot_service/app/services/websocket_manager.py`
- Create: `bot_service/app/routes/ws_chat.py`
- Create: `frontend/streamlit_app.py`

- [ ] `team.py`: `criar_time(session_id)` com só Triagem por enquanto, padrão passthrough
- [ ] `websocket_manager.py`: copiado/adaptado do V1 (`conexao`, `enviar_mensagem`, `desconexao`)
- [ ] `ws_chat.py`: endpoint `/chat/ws/{session_id}`, processa mensagem via team, envia resposta + `STREAM_END_TOKEN`
- [ ] `streamlit_app.py`: chat baseado no `streamlit_app.py` do V1, conecta WS na 8000
- [ ] Teste E2E manual: Streamlit → digita CLI001 → recebe e-mail no Mailpit (8025) → digita código → autenticado
- [ ] **Commit Phase 4:** `feat: V2 phase 4 - Triagem + OTP por e-mail + WebSocket + Streamlit`

---

## Fase 5 — Agentes informativos (Saldo, Contas, Câmbio)

### Task 5.1: Tools do gateway para saldo e contas

**Files:**
- Create: `bot_service/app/tools/gateway_tools.py`

- [ ] `obter_saldo_cliente(session_id)` → usa session de auth para pegar id_cliente, chama gateway_client
- [ ] `obter_contas_cliente(session_id, tipo, periodo)` → idem

### Task 5.2: agente_saldo.py + agente_contas.py + agente_cambio.py

- [ ] `agente_saldo.py`: instruções para apresentar saldo formatado em R$
- [ ] `agente_contas.py`: lista contas em tabela markdown, agrupando por tipo
- [ ] `agente_cambio.py`: usa `TavilyTools()`, formata cotações em tabela

### Task 5.3: Atualizar Team com roteamento

- [ ] Team agora tem 4 agentes (Triagem, Saldo, Contas, Cambio)
- [ ] Instruções de roteamento conforme spec §4.1
- [ ] Testes: mock gateway, simula mensagens, verifica que o agente certo é selecionado
- [ ] **Commit Phase 5:** `feat: V2 phase 5 - agentes Saldo, Contas, Cambio`

---

## Fase 6 — Crédito + Entrevista

### Task 6.1: Service de score/limite no gateway

**Files:**
- Create: `banking_gateway/app/api/{rotas_credito.py}`

- [ ] Migrar lógica de `tools/tools.py` do V1 para o gateway
- [ ] `GET /credito/limite/{id_cliente}` → limite atual
- [ ] `POST /credito/solicitar-aumento` body `{id_cliente, novo_limite}` → cria `solicitacoes_limite`, calcula faixa permitida via `score_credito_base`, retorna aprovado/rejeitado
- [ ] `POST /credito/atualizar-score` body `{id_cliente, renda, tipo_emprego, despesas, dependentes, dividas}` → aplica fórmula da spec, atualiza cliente
- [ ] Testes: cada cenário (aprovado, rejeitado por score, valor inválido)

### Task 6.2: Tools no bot_service

- [ ] `tools/credito_tools.py`: `consultar_limite(session_id)`, `solicitar_aumento_limite(session_id, valor)` (este último usa **step-up** — abordado na Fase 7), `atualizar_score(session_id, ...)`

### Task 6.3: Agentes Credito e Entrevista

- [ ] `agente_credito.py`: instrutções do V1 adaptadas (apenas consulta nesta fase, aumento vem na 7)
- [ ] `agente_entrevista.py`: 5 perguntas, coleta, chama tool no final
- [ ] Atualizar Team com 6 agentes
- [ ] **Commit Phase 6:** `feat: V2 phase 6 - agentes Credito (consulta) e Entrevista`

---

## Fase 7 — Step-Up 2FA + Transações + aumento de limite

### Task 7.1: Confirmações pendentes (gateway)

**Files:**
- Create: `banking_gateway/app/api/rotas_confirmacao.py`
- Create: `banking_gateway/app/templates/{confirmacao.html,sucesso.html,erro.html,expirado.html}`
- Create: `banking_gateway/app/static/style.css`

- [ ] Service: `criar_confirmacao(id_cliente, dados_transacao)` retorna token+url, expira em 10min
- [ ] `GET /confirmar/{token}` → renderiza `confirmacao.html` com dados da operação
- [ ] `POST /confirmar/{token}` form `{senha}` → valida senha_hash, executa operação real (insere transacao OU atualiza limite), marca CONFIRMADA, redireciona para `sucesso.html`
- [ ] Tratamento: token inválido → erro.html, expirado → expirado.html, senha errada (3 tentativas) → REJEITADA
- [ ] Rate limit 5/min por IP no POST
- [ ] Testes: fluxo feliz, senha errada, expirado, 3 tentativas

### Task 7.2: Agente Transacoes

**Files:**
- Create: `bot_service/app/agents/agente_transacoes.py`
- Create: `bot_service/app/tools/transacao_tools.py`

- [ ] Tool `iniciar_criacao_transacao(session_id, tipo, descricao, valor, data_vencimento, ...)` → cria confirmação, retorna URL
- [ ] Agente conduz coleta (descrição, valor, data) e dispara confirmação

### Task 7.3: Aumento de limite com step-up

- [ ] Reescrever tool `solicitar_aumento_limite` para gerar confirmação ao invés de aprovar direto
- [ ] Agente Credito orienta o cliente a abrir o link

### Task 7.4: Detecção de link no Streamlit

- [ ] Regex no texto da resposta; se casar URL `/confirmar/...`, mostra botão Markdown `[🔒 Abrir confirmação](url)` que abre em nova aba
- [ ] Atualizar Team com 7 agentes finais
- [ ] **Commit Phase 7:** `feat: V2 phase 7 - Step-Up 2FA, agente Transacoes, aumento de limite via web`

---

## Fase 8 — Polimento

### Task 8.1: Rate limiting + structlog + correlation_id

- [ ] slowapi nas rotas sensíveis (já feitas), confirmar coberto
- [ ] middleware injeta `correlation_id` no contextvar
- [ ] Eventos logados conforme spec §8.3

### Task 8.2: Cobertura ≥ 80%

- [ ] `pytest --cov=assistente_bancario_v2 --cov-report=term-missing` — relatório
- [ ] Adicionar testes faltantes até bater 80%

### Task 8.3: Lint + types limpos

- [ ] `ruff check .` zero erros
- [ ] `mypy assistente_bancario_v2` zero erros

### Task 8.4: README com diagrama, quickstart, troubleshooting

- [ ] README explicando arquitetura, env vars, como rodar (docker e local), como testar, como acessar Mailpit
- [ ] **Commit Phase 8:** `feat: V2 phase 8 - polimento, coverage, lint, README`

---

## Notas

- **Commits frequentes:** ao final de cada Task, commit. Ao final de cada Fase, commit consolidado se houver pendências.
- **Branches:** trabalhar diretamente em `main` da subpasta `v2/` (mesmo repo).
- **Rollback:** cada Fase tem testes — se quebrar, `git revert` da Fase.
- **Variáveis Gemini/Tavily:** usuário precisa preencher em `.env` antes de testar agentes em produção. Mailpit funciona offline.
