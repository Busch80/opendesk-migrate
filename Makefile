.PHONY: help install lint test build dev up down logs shell seed migration upgrade reset clean rotate-fernet

# Config ---------------------------------------------------------------------
PYTHON ?= python3
NODE   ?= node
DOCKER_COMPOSE ?= docker compose
SHELL_ASH      = docker compose exec api bash
SHELL_NODE     = docker compose exec web sh

help:                ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Install --------------------------------------------------------------------
install:              ## Install all deps (api + web)
	cd api && $(PYTHON) -m pip install -e ".[dev]"
	cd web && $(NODE) install

# Lint ------------------------------------------------------------------------
lint:                ## Run linters (ruff + mypy + eslint)
	cd api && ruff check .
	cd api && ruff format --check .
	cd api && mypy app
	cd web && npm run lint

format:              ## Auto-format code (ruff + prettier)
	cd api && ruff format .
	cd web && npm run format

# Tests -----------------------------------------------------------------------
test:                ## Run all tests + coverage
	cd api && pytest --cov=app --cov-report=term-missing

test-unit:           ## Run unit tests only
	cd api && pytest -m unit

test-integration:    ## Run integration tests
	cd api && pytest -m integration

# Local dev -------------------------------------------------------------------
build:               ## Build all docker images
	$(DOCKER_COMPOSE) build

up:                  ## Start all services in background
	$(DOCKER_COMPOSE) up -d

down:                ## Stop all services
	$(DOCKER_COMPOSE) down

dev: build up logs   ## Build + up + tail logs

logs:                ## Tail logs of all services
	$(DOCKER_COMPOSE) logs -f --tail=100

shell-api:           ## Open bash in API container
	$(SHELL_ASH)

shell-web:           ## Open sh in Web container
	$(SHELL_NODE)

shell-postgres:      ## Open psql in Postgres container
	$(DOCKER_COMPOSE) exec postgres psql -U odmig -d odmig

shell-redis:         ## Open redis-cli in Redis container
	$(DOCKER_COMPOSE) exec redis redis-cli

# DB migrations ---------------------------------------------------------------
migration:           ## Generate a new Alembic migration (msg=…)
	cd api && alembic revision --autogenerate -m "$(msg)"

upgrade:             ## Apply all pending Alembic migrations
	$(DOCKER_COMPOSE) exec api alembic upgrade head

reset:               ## Reset Postgres (destroys data)
	@read -p "Are you sure? [type YES to confirm] " R && [ "$$R" = "YES" ]
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d postgres redis
	sleep 5
	$(DOCKER_COMPOSE) up api worker-maintenance beat

# Utilities -------------------------------------------------------------------
rotate-fernet:       ## Generate a new FERNET_KEY value
	cd api && $(PYTHON) -c "from app.services.encryption import generate_fernet_key; print(generate_fernet_key())"

rotate-secret:       ## Generate a new SECRET_KEY value
	$(PYTHON) -c "import secrets; print(secrets.token_urlsafe(48))"

clean:               ## Clean up caches, __pycache__, .pytest_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf api/dist web/dist .coverage
