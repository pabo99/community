# Community platform — developer interface.
# Stable command vocabulary per docs/technical-design.md §12.
# Some targets delegate to tooling introduced by later M1 issues; they are
# defined now so the interface stays stable as services arrive.

COMPOSE := docker compose

.PHONY: up down logs logs-api logs-worker test test-backend test-frontend test-e2e \
        migrate migration lint format db-shell seed

# --- Stack lifecycle ---
up:
	$(COMPOSE) up -d

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

test-backend:
	@echo "test-backend: backend test runner is introduced in M1-02/M1-03."

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
	@echo "lint: lint tooling is introduced in M1-02 (backend) / M1-04 (frontend)."

format:
	@echo "format: formatter is introduced in M1-02."

# --- Seed/demo data (introduced in M1-13) ---
seed:
	@echo "seed: development seed data is introduced in M1-13."
