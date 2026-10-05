# Milestone 1 — Foundation & First Edition

## Goal

> A developer can run the platform locally, sign in with GitHub, and an administrator can create and configure an edition.

This milestone proves the core architecture end-to-end without prematurely implementing the full contributor-program feature set.

## Definition of Done

A fresh developer checkout can complete this path:

```text
git clone
  ↓
cp .env.example .env
  ↓
make up
  ↓
database migrations
  ↓
WebApp loads
  ↓
Login with GitHub
  ↓
Admin area
  ↓
Create an edition
  ↓
Edition is persisted in PostgreSQL and reloads correctly
```

Additionally:

- API and frontend automated checks pass in CI.
- PostgreSQL migrations can build the current schema from an empty database.
- Worker/job infrastructure executes at least one deterministic job end-to-end.
- Health endpoints work.
- Seed/demo data is available for development.
- README contains working local setup instructions.

## Explicitly out of scope

Do not implement these in Milestone 1 unless a foundation task strictly requires a minimal abstraction:

- GitHub repository mirror/synchronization
- omegaUp scoreboard/scoreboardEvents synchronization
- Discord integration
- video-review workflow
- contribution qualification rules
- proposals/design-document review workflow
- announcements
- recognitions/+1
- mentor evaluation
- project-sensitive ranking
- full program-phase wizard
- production SOPS/secrets design
- Neon migration

## Proposed issues

### M1-01 — Bootstrap monorepo and developer tooling

Create the initial repository structure for backend, frontend, E2E, docs, Docker Compose, Makefile, `.env.example`, README, and AGENTS.md.

**Acceptance criteria**

- Repository structure follows `docs/technical-design.md`.
- `docker compose config` succeeds.
- `.env.example` contains safe development placeholders only.
- Real `.env` files are ignored.
- Makefile contains initial `up`, `down`, `logs`, and `test` entry points (commands may delegate to later tasks until services exist).
- README explains the intended local workflow.

**Dependencies:** none.

---

### M1-02 — Bootstrap FastAPI backend

Create the backend application with configuration loading, structured project layout, and development server.

**Acceptance criteria**

- FastAPI application starts in Docker.
- `GET /health/live` returns success.
- OpenAPI docs are available in development.
- Pydantic-based settings fail clearly for missing required configuration.
- Initial pytest setup exists and tests the liveness endpoint.
- Ruff and mypy configuration exists.

**Dependencies:** M1-01.

---

### M1-03 — Add PostgreSQL, SQLAlchemy, psycopg, and Alembic

Introduce PostgreSQL 17 and the backend persistence foundation.

**Acceptance criteria**

- PostgreSQL runs through Docker Compose and is not exposed publicly by default.
- SQLAlchemy 2.x session management is configured.
- psycopg 3 is used.
- Alembic is initialized and can migrate an empty DB to `head`.
- `GET /health/ready` verifies required DB readiness without checking external services.
- Integration test runs against PostgreSQL, not SQLite.
- Makefile provides migration and DB-shell commands.

**Dependencies:** M1-02.

---

### M1-04 — Bootstrap Vue 3 frontend

Create the Vue SPA foundation.

**Acceptance criteria**

- Vue 3 + TypeScript + Vite runs in Docker with HMR.
- Vue Router and Pinia are configured.
- PrimeVue and Tailwind CSS are configured and demonstrably usable.
- A basic application shell and unauthenticated landing/login view exist.
- Vitest + Vue Test Utils are configured with at least one meaningful test.
- ESLint and `vue-tsc` checks are configured.

**Dependencies:** M1-01.

---

### M1-05 — Establish Person and ExternalIdentity schema

Implement the minimum identity domain required for GitHub authentication.

**Acceptance criteria**

- `Person` and `ExternalIdentity` models exist.
- External identity records support provider, stable external identifier where available, username/display identifier, and verification metadata.
- A person can have multiple external identities.
- GitHub identity uniqueness invariants are enforced in PostgreSQL.
- Alembic migration is included and reviewed.
- Model/repository integration tests exist.

**Dependencies:** M1-03.

---

### M1-06 — Implement GitHub OAuth login and server-side sessions

Implement production GitHub authentication without introducing application JWTs in browser storage.

**Acceptance criteria**

- User can initiate GitHub OAuth and complete callback.
- Login finds/creates Person + GitHub ExternalIdentity.
- Server-side session is created.
- Browser uses an HttpOnly session cookie with environment-appropriate security settings.
- Logout invalidates the session.
- `GET /api/me` returns the authenticated user's safe profile.
- Anonymous access to authenticated endpoints returns `401`.
- OAuth/session secrets never appear in logs.
- Tests mock GitHub OAuth rather than calling GitHub live.

**Dependencies:** M1-05.

---

### M1-07 — Add authorization foundation and bootstrap admin

Introduce platform-level admin authorization while keeping ordinary authenticated users unprivileged.

**Acceptance criteria**

- Platform admin role/authorization model exists.
- Development/bootstrap mechanism can designate the initial admin without hardcoding a personal username in application logic.
- Backend dependency/policy enforces admin endpoints.
- Contributor/non-admin receives `403` for admin endpoints.
- Frontend can hide/guard admin navigation for UX, while backend remains authoritative.
- Authorization tests cover anonymous, authenticated non-admin, and admin cases.

**Dependencies:** M1-06.

---

### M1-08 — Implement Program and Edition domain

Add the minimum reusable program/edition model.

**Acceptance criteria**

- Program and Edition relational models exist.
- Edition belongs to a Program.
- Edition supports at least name/title, identifier/slug, lifecycle status, and relevant date boundaries needed by the initial admin screen.
- Domain does not hardcode GSoC as the only program type.
- Alembic migration is included.
- Constraints and tests cover important invariants.

**Dependencies:** M1-03.

---

### M1-09 — Implement admin Program/Edition REST API

Expose the first real product-management API.

**Acceptance criteria**

- Admin can list/create/read/update Programs and Editions as required by the initial UI.
- Endpoints use explicit Pydantic request/response schemas rather than exposing ORM models.
- Non-admin access is forbidden.
- API validation produces useful errors.
- OpenAPI reflects the contracts.
- API tests cover happy paths, validation, authorization, and persistence.

**Dependencies:** M1-07, M1-08.

---

### M1-10 — Implement Edition admin UI

Build the first end-to-end product workflow.

**Acceptance criteria**

- Admin can navigate to edition administration.
- Admin can create a Program/Edition through the WebApp.
- Admin can view and edit the initial Edition fields.
- Reloading the application shows persisted data from PostgreSQL.
- Non-admin users cannot use the admin UI and remain protected by backend authorization.
- Loading, empty, validation-error, and server-error states are handled.
- Frontend tests cover important behavior.

**Dependencies:** M1-04, M1-09.

---

### M1-11 — Add PostgreSQL-backed job infrastructure

Implement the minimal asynchronous job foundation without GitHub/omegaUp synchronization yet.

**Acceptance criteria**

- Persistent jobs table supports type, payload, status, attempts, scheduling timestamps, execution timestamps, and error information.
- Python worker runs as a separate Docker Compose service using the backend image/codebase.
- Worker claims jobs safely using PostgreSQL locking suitable for multiple workers (`FOR UPDATE SKIP LOCKED` or equivalent correct implementation).
- At least one deterministic demonstration job completes `PENDING → RUNNING → SUCCEEDED`.
- Recoverable failure/retry behavior has automated coverage.
- No Redis/RabbitMQ/Celery dependency is introduced.

**Dependencies:** M1-03.

---

### M1-12 — Add scheduler foundation

Introduce APScheduler only as a producer of jobs, not as the executor of long-running integration work.

**Acceptance criteria**

- Scheduler can enqueue a deterministic periodic demonstration job.
- Job execution remains the worker's responsibility.
- Duplicate scheduling behavior is understood/prevented where required.
- Scheduler can be disabled cleanly in tests/development scenarios where appropriate.
- Automated tests cover scheduling behavior without depending on wall-clock sleeps.

**Dependencies:** M1-11.

---

### M1-13 — Add seed/demo data and test authentication support

Make local UI/product development possible without real external credentials.

**Acceptance criteria**

- `make seed` creates deterministic development data including at least admin and ordinary-user scenarios plus a sample Program/Edition.
- Seed command is safe for development and documented.
- Test/E2E authentication mechanism is available only in explicit test/development configuration and cannot be accidentally enabled in production.
- Frontend development can exercise authenticated/admin screens without depending on live GitHub OAuth when test mode is selected.

**Dependencies:** M1-07, M1-08.

---

### M1-14 — Establish critical E2E foundation

Configure Playwright and cover the milestone's core vertical path.

**Acceptance criteria**

- Playwright runs against the containerized test application.
- Critical E2E covers: authenticate as admin → open admin → create edition → reload/read persisted edition.
- E2E uses deterministic test authentication, not live GitHub OAuth.
- Test data isolation/reset strategy is documented.
- No blind retry policy is used to hide flaky behavior.

**Dependencies:** M1-10, M1-13.

---

### M1-15 — Add GitHub Actions CI

Make the milestone continuously verifiable.

**Acceptance criteria**

- Backend CI runs Ruff, mypy, pytest, PostgreSQL integration tests, and Alembic `upgrade head` from an empty DB.
- Frontend CI runs ESLint, `vue-tsc`, Vitest, and production Vite build.
- Docker images/builds are validated.
- Critical Playwright workflow runs in CI.
- Workflows use dependency caching appropriately and do not require production secrets.
- Required-check recommendations are documented for branch protection.

**Dependencies:** M1-02, M1-03, M1-04, M1-14.

---

### M1-16 — Add structured logging and request/job correlation

Implement the minimum observability foundation needed before deployment.

**Acceptance criteria**

- Backend/worker use structured logging rather than `print` for operational events.
- Production formatting can emit JSON to stdout/stderr.
- HTTP requests receive a request/correlation ID.
- Job logs include job ID and type.
- Sensitive headers/cookies/secrets are not logged.
- Logging behavior has focused automated coverage where practical.

**Dependencies:** M1-02, M1-11.

---

### M1-17 — Complete developer documentation and milestone smoke test

Validate the project from a clean-checkout perspective.

**Acceptance criteria**

- README documents prerequisites and the shortest supported setup path.
- `cp .env.example .env` + documented commands can start the development stack.
- Migration, seed, test, logs, and shutdown commands are documented.
- Architecture/product docs are linked from README.
- A clean environment can complete the Milestone Definition of Done path.
- Known deferred decisions (including production secret/SOPS strategy) are explicitly recorded rather than accidentally implemented ad hoc.

**Dependencies:** all other M1 issues.

## Recommended execution order

```text
M1-01
 ├─ M1-02 ─ M1-03 ─┬─ M1-05 ─ M1-06 ─ M1-07 ─┬─ M1-09 ─ M1-10 ─┐
 │                  │                           │                  │
 │                  ├─ M1-08 ──────────────────┘                  ├─ M1-14
 │                  │                                              │
 │                  └─ M1-11 ─ M1-12                              │
 │                           └─────────────── M1-16                 │
 │                                                                 │
 └─ M1-04 ──────────────────────────────────────── M1-10           │
                                                                    │
                    M1-13 ──────────────────────────────────────────┘
                                                                    │
                                                   M1-15 ───────────┤
                                                                    ▼
                                                                  M1-17
```

Parallelism is encouraged after the bootstrap, but schema/auth/security foundation changes should be reviewed before large dependent branches build on them.

## Kiro execution policy for M1

Do not ask Kiro to implement the entire milestone in one prompt.

For each issue:

1. Give Kiro the issue text and ask it to read `AGENTS.md`, `docs/product-design.md`, and `docs/technical-design.md` first.
2. For non-trivial issues, require a plan before implementation.
3. Review the plan for schema/auth/authorization/jobs changes.
4. Let Kiro implement and run tests.
5. Review the resulting diff/test summary.
6. Merge before beginning heavily dependent work.

This keeps the architecture adjustable while the foundation is still young.
