.PHONY: help env build up down logs restart ps clean test test-cov local local-stop

COMPOSE = docker compose -f infra/docker-compose.yml --env-file .env

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "} {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

env: ## Cria .env a partir de .env.example (se ainda não existir)
	@test -f .env || (cp .env.example .env && echo "✓ .env criado — edite GEMINI_API_KEY antes de subir")

build: env ## Builda as 3 imagens (gateway, bot, streamlit)
	$(COMPOSE) build

up: env ## Sobe a stack toda (em background)
	$(COMPOSE) up -d
	@echo ""
	@echo "✓ Stack rodando:"
	@echo "  · Streamlit  http://localhost:$${STREAMLIT_PORT:-8501}"
	@echo "  · Bot docs   http://localhost:$${BOT_PORT:-8000}/docs"
	@echo "  · Gateway    http://localhost:$${GATEWAY_PORT:-8001}/docs"
	@echo "  · Mailpit    http://localhost:$${MAILPIT_UI_PORT:-8025}"

down: ## Derruba a stack (mantém volumes)
	$(COMPOSE) down

down-clean: ## Derruba a stack e remove volumes
	$(COMPOSE) down -v

logs: ## Acompanha logs (tail -f)
	$(COMPOSE) logs -f --tail=100

logs-bot: ## Logs apenas do bot
	$(COMPOSE) logs -f --tail=200 bot

logs-gateway: ## Logs apenas do gateway
	$(COMPOSE) logs -f --tail=200 gateway

restart: ## Restart da stack
	$(COMPOSE) restart

ps: ## Status dos serviços
	$(COMPOSE) ps

shell-bot: ## Shell dentro do container bot
	$(COMPOSE) exec bot /bin/sh

shell-gateway: ## Shell dentro do container gateway
	$(COMPOSE) exec gateway /bin/sh

test: ## Roda os testes (precisa do venv local)
	. .venv/bin/activate && PYTHONPATH=. DEBUG=true pytest -v

test-cov: ## Roda os testes com cobertura
	. .venv/bin/activate && PYTHONPATH=. DEBUG=true pytest --cov=assistente_bancario_v2 --cov-report=term-missing

local: env ## Sobe localmente (sem docker) gateway + bot + streamlit
	./scripts/run_dev.sh start

local-stop: ## Para os serviços locais
	./scripts/run_dev.sh stop

clean: ## Limpa caches e venv
	rm -rf .venv .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
