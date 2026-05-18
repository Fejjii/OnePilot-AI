# OnePilot AI — developer convenience targets
# Requires: Python 3.11+, Node 20+, pnpm, Docker, Docker Compose
#
# Cross-platform note: most targets assume a Unix-like shell (bash/zsh).
# On Windows, use Git Bash, WSL, or run the commands directly.

.PHONY: help \
        infra infra-down \
        backend-install backend-migrate backend-seed backend-dev backend-test backend-lint \
        frontend-install frontend-dev frontend-build frontend-test frontend-lint \
        docker-build docker-up docker-down docker-logs docker-migrate docker-seed \
        check-stack reset-demo \
        test lint

# ── Default ───────────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure only (local dev) ──────────────────────────────────────────
infra: ## Start Postgres, Redis, Qdrant in Docker (local dev)
	docker compose up -d postgres redis qdrant

infra-down: ## Stop infrastructure containers
	docker compose stop postgres redis qdrant

# ── Backend (local dev) ───────────────────────────────────────────────────────
backend-install: ## Install backend dependencies (editable + dev extras)
	cd backend && pip install -e ".[dev]"

backend-migrate: ## Run Alembic migrations (requires DATABASE_URL)
	cd backend && alembic upgrade head

backend-seed: ## Seed NovaEdge demo data via HTTP (backend must be running)
	cd backend && python scripts/seed_demo.py

backend-dev: ## Start backend dev server with hot reload on :8000
	cd backend && uvicorn onepilot.api.main:app --reload --port 8000

backend-test: ## Run the full pytest suite
	cd backend && pytest -v

backend-lint: ## Run Ruff linter and formatter check
	cd backend && ruff check src tests && ruff format --check src tests

# ── Frontend (local dev) ──────────────────────────────────────────────────────
frontend-install: ## Install frontend dependencies via pnpm
	cd frontend && pnpm install

frontend-dev: ## Start Next.js dev server on :3000
	cd frontend && pnpm dev

frontend-build: ## Production build (typecheck + build)
	cd frontend && pnpm build

frontend-test: ## Run Vitest test suite
	cd frontend && pnpm test

frontend-lint: ## Run ESLint + tsc typecheck
	cd frontend && pnpm lint && pnpm typecheck

# ── Full Docker stack ─────────────────────────────────────────────────────────
docker-build: ## Build all Docker images
	docker compose build

docker-up: ## Start the full stack (infra + backend + frontend)
	docker compose up -d

docker-down: ## Stop and remove all containers
	docker compose down

docker-logs: ## Follow logs for all services
	docker compose logs -f

docker-migrate: ## Run Alembic migrations inside Docker
	docker compose run --rm migrate

docker-seed: ## Seed demo data inside Docker (requires running backend)
	docker compose run --rm seed

# ── Quality / CI shortcuts ────────────────────────────────────────────────────
test: backend-test frontend-test ## Run all tests (backend + frontend)

lint: backend-lint frontend-lint ## Run all linters (backend + frontend)

# ── Utilities ─────────────────────────────────────────────────────────────────
check-stack: ## Check that all services are healthy
	cd backend && python scripts/check_stack.py

reset-demo: ## Wipe and re-seed demo data (destructive)
	@echo "Wiping demo data and re-seeding..."
	cd backend && python scripts/seed_demo.py --reset

setup: ## Full first-time setup: install deps, start infra, migrate, seed
	$(MAKE) infra
	@echo "Waiting for Postgres to be ready..."
	sleep 5
	$(MAKE) backend-install
	$(MAKE) backend-migrate
	$(MAKE) backend-seed
	$(MAKE) frontend-install
	@echo ""
	@echo "Setup complete. Run 'make backend-dev' and 'make frontend-dev' in separate terminals."
