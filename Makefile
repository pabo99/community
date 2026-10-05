# Community platform — developer interface.
# Stable command vocabulary per docs/technical-design.md §12.
# Some targets delegate to tooling introduced by later M1 issues; they are
# defined now so the interface stays stable as services arrive.

COMPOSE := docker compose

.PHONY: up down logs logs-api logs-worker test test-backend test-frontend test-e2e \
        migrate migration lint format db-shell seed

# --- Stack lifecycle ---
# Start the services available at this milestone. The worker runtime behavior
# is introduced in M1-11; until then the worker service is not started.
up:
	$(COMPOSE) up -d db api

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

logs-api:
	$(COMPOSE) logs -f api

logs-worker:
	$(COMPOSE) logs -f worker

# --- Tests (implementations arrive with backend/frontend/e2e issues) ---
test: test-backend test-frontend

# Dev-only checks mount the full backend tree (tests are not baked into the
# image) and sync the dev dependency group into the image's virtualenv.
BACKEND_RUN := $(COMPOSE) run --rm --no-deps -v ./backend:/app -w /app api

test-backend:
	$(BACKEND_RUN) uv run --frozen --group dev pytest

test-frontend:
	@echo "test-frontend: frontend test runner is introduced in M1-04."

test-e2e:
	@echo "test-e2e: Playwright E2E is introduced in M1-14."

# --- Database / migrations (introduced in M1-03) ---
migrate:
	@echo "migrate: Alembic migrations are introduced in M1-03."

migration:
	@echo "migration name=\"...\": Alembic autogeneration is introduced in M1-03."

db-shell:
	@echo "db-shell: database shell is introduced in M1-03."

# --- Code quality (introduced with backend/frontend issues) ---
lint:
	$(BACKEND_RUN) uv run --frozen --group dev ruff check
	$(BACKEND_RUN) uv run --frozen --group dev mypy
	@echo "lint: frontend lint is introduced in M1-04."

format:
	$(BACKEND_RUN) uv run --frozen --group dev ruff format

# --- Seed/demo data (introduced in M1-13) ---
seed:
	@echo "seed: development seed data is introduced in M1-13."
