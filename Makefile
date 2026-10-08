# Community platform — developer interface.
# Stable command vocabulary per docs/technical-design.md §12.
# Some targets delegate to tooling introduced by later M1 issues; they are
# defined now so the interface stays stable as services arrive.

COMPOSE := docker compose

.PHONY: up down logs logs-api logs-worker test test-backend test-frontend test-e2e \
        db-up test-db-create migrate migration lint format format-check db-shell seed

# --- Stack lifecycle ---
# Start the services available at this milestone. The worker runtime behavior
# is introduced in M1-11; until then the worker service is not started.
up:
	$(COMPOSE) up -d db api frontend

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
# --no-deps keeps lint/format from starting the database; the test target
# below starts a healthy db itself so developers never need `make up` first.
BACKEND_RUN := $(COMPOSE) run --rm --no-deps -v ./backend:/app -w /app api

# Start PostgreSQL and wait until it is healthy (used by test-backend).
db-up:
	$(COMPOSE) up -d --wait db

# Create the integration-test database (<POSTGRES_DB>_test) on the same service
# if it is missing. Uses the db container's own env, so Make does not need the
# value. Safe to run repeatedly; a pre-existing database is left untouched.
test-db-create: db-up
	$(COMPOSE) exec -T db sh -c \
	  'psql -U "$$POSTGRES_USER" -tc "SELECT 1 FROM pg_database WHERE datname = '\''$${POSTGRES_DB}_test'\''" | grep -q 1 \
	  || psql -U "$$POSTGRES_USER" -c "CREATE DATABASE $${POSTGRES_DB}_test"'

# Runs the full backend suite (unit + real-PostgreSQL integration). Ensures the
# database service is up/healthy and the test database exists first, so no
# `make up` is required beforehand. Joins the compose network to reach db.
test-backend: test-db-create
	$(COMPOSE) run --rm -v ./backend:/app -w /app api \
	  uv run --frozen --group dev pytest

# Runs the frontend unit suite once (not watch mode) in the frontend image.
# --no-deps avoids starting api/db just to run frontend unit tests.
FRONTEND_RUN := $(COMPOSE) run --rm --no-deps frontend

test-frontend:
	$(FRONTEND_RUN) npm run test:run

test-e2e:
	@echo "test-e2e: Playwright E2E is introduced in M1-14."

# --- Database / migrations ---
# Apply all migrations up to head against the development database. Ensures the
# database is up/healthy first so a fresh checkout works without `make up`.
migrate: db-up
	$(COMPOSE) run --rm -v ./backend:/app -w /app api \
	  uv run --frozen alembic upgrade head

# Autogenerate a new revision: `make migration name="add something"`.
# Autogenerate compares models to the database; it produces an empty revision
# until domain models exist (M1-05 onward).
migration: db-up
	@test -n "$(name)" || (echo 'usage: make migration name="description"' && exit 1)
	$(COMPOSE) run --rm -v ./backend:/app -w /app api \
	  uv run --frozen alembic revision --autogenerate -m "$(name)"

# Open an interactive psql shell in the running development database.
db-shell:
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# --- Code quality ---
# lint: backend Ruff + mypy, frontend ESLint + vue-tsc.
lint:
	$(BACKEND_RUN) uv run --frozen --group dev ruff check
	$(BACKEND_RUN) uv run --frozen --group dev mypy
	$(FRONTEND_RUN) npm run lint
	$(FRONTEND_RUN) npm run type-check

# format: backend Ruff format, frontend Prettier (mutating).
format:
	$(BACKEND_RUN) uv run --frozen --group dev ruff format
	$(FRONTEND_RUN) npm run format

# format-check: non-mutating formatting verification for both packages,
# suitable for validation and future CI.
format-check:
	$(BACKEND_RUN) uv run --frozen --group dev ruff format --check
	$(FRONTEND_RUN) npm run format:check

# --- Seed/demo data (introduced in M1-13) ---
seed:
	@echo "seed: development seed data is introduced in M1-13."
