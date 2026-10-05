# AGENTS.md

## Project context

This repository implements the Contributor Community Platform for omegaUp-related contributor programs.

Before planning or implementing non-trivial changes, read:

1. `docs/product-design.md`
2. `docs/technical-design.md`

These documents are the current product and architectural source of truth. If an issue conflicts with them, stop and surface the conflict rather than silently changing architecture.

## Core rules

- GitHub is the source of truth for issues, pull requests, reviews, labels, milestones, and contribution state.
- omegaUp is the source of truth for omegaUp contest/test activity.
- The GitHub local replica is partial and reconstructible.
- Never perform GitHub or omegaUp synchronization synchronously inside a normal HTTP request.
- HTTP endpoints that request synchronization enqueue a job and return promptly (normally `202 Accepted`).
- A GitHub pull request counts as completed only when it is merged.
- Contributor omegaUp API tokens are ephemeral identity-verification credentials. Never persist or log them.
- Internal mentor evaluations, scores, ranking notes, and rankings must never be exposed through contributor-facing APIs.
- Backend authorization is authoritative. Frontend route guards are UX only.
- PostgreSQL is the only required persistence/queue service in V1. Do not add Redis, RabbitMQ, Celery, or another broker without an explicit architecture decision.
- All production schema changes require Alembic migrations.
- Do not use SQLite as a substitute for PostgreSQL integration tests.
- New or changed business rules require tests.
- Do not disable, weaken, skip, or add blind retries to failing tests merely to complete a task.
- Do not add provider-specific database dependencies when standard PostgreSQL is sufficient.
- Never commit credentials, `.env` files, tokens, private keys, or production secrets.
- Never log authorization headers, cookies, API tokens, OAuth secrets, scoreboard tokens, or password-bearing connection strings.

## Technology baseline

Backend:

- Python 3.13 target
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- psycopg 3
- Alembic
- PostgreSQL 17

Frontend:

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- PrimeVue
- Tailwind CSS

Integration/background work:

- GitHub GraphQL
- omegaUp APIs
- Python worker
- PostgreSQL-backed job queue
- APScheduler

Testing:

- pytest
- real PostgreSQL integration tests
- Vitest + Vue Test Utils
- Playwright for a small critical E2E suite

CI/CD:

- GitHub Actions
- Docker Compose for local development and initial VPS deployment

## Implementation workflow

For each issue:

1. Read the issue and relevant design sections.
2. Inspect existing implementation before proposing changes.
3. Produce a concise implementation plan for non-trivial work.
4. Keep the change scoped to the issue.
5. Add/update tests as part of the same change.
6. Run the narrowest relevant checks during implementation, then the required full checks before completion.
7. Summarize changed files, migrations, API changes, tests run, and any remaining risks/decisions.

Do not opportunistically refactor unrelated areas unless required for correctness. If a broader architectural improvement is discovered, describe it separately.

## API conventions

- REST + OpenAPI.
- Use explicit Pydantic request/response models.
- Keep contributor and internal mentor/admin response models separate when data visibility differs.
- Avoid leaking ORM models directly as API contracts.
- Long-running work belongs in jobs, not request handlers.

## Database conventions

- Prefer explicit relational modeling for domain entities and relationships.
- Use JSONB only for genuinely type-specific flexible configuration and validate it with Pydantic.
- Preserve constraints and indexes that encode important invariants.
- Review Alembic autogeneration before committing migrations.
- Design jobs to be idempotent or explicitly document non-idempotent behavior/recovery requirements.

## External integration conventions

Normal automated tests must not depend on live GitHub or omegaUp services. Use realistic fixtures and HTTP mocks. Live contract checks belong in explicitly designated/manual/nightly workflows.

Integration failures should degrade to stale local data where possible rather than make the entire WebApp unavailable.

## Frontend conventions

- PrimeVue handles complex reusable UI behavior/components.
- Tailwind handles layout, spacing, responsive composition, and product visual identity.
- Do not duplicate backend authorization assumptions in frontend-only logic.
- Keep Pinia for genuinely shared/global state; do not put every API response into a global store.
- Prefer generated OpenAPI TypeScript contracts/client tooling when introduced.

## Definition of done

An implementation is not complete until:

- acceptance criteria are satisfied,
- migrations are included when schema changes,
- relevant automated tests pass,
- lint/type checks pass for touched areas,
- documentation is updated when behavior/contracts/architecture change,
- no secrets or sensitive internal data are exposed.
