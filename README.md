# community

Community and contributor management platform for omegaUp.

A standalone platform for managing and supporting omegaUp contributors across
programs such as Google Summer of Code, internships, school residencies, and
volunteer initiatives. It complements GitHub and omegaUp rather than replacing
either: GitHub stays the source of truth for contribution work, and omegaUp
stays the source of truth for contest/test activity.

## Documentation

- [Product design](docs/product-design.md) — product scope, concepts, and workflows.
- [Technical design](docs/technical-design.md) — architecture, stack, and repository shape.
- [Milestone 1](docs/milestone-1.md) — foundation and first-edition plan.
- [AGENTS.md](AGENTS.md) — core rules and conventions for contributors and agents.

## Repository structure

The repository follows the shape documented in
[technical-design.md §12](docs/technical-design.md). Directories are created as
each milestone issue delivers its part of the stack:

```text
community/
├── backend/    FastAPI app + worker (same image, different commands)
├── frontend/   Vue 3 + Vite SPA
├── e2e/        Playwright critical-path suite
├── docs/       product/technical/milestone docs
├── docker-compose.yml
├── Makefile
└── .env.example
```

## Local development

The official local environment is Docker Compose. The four-service topology
(`frontend`, `api`, `worker`, `db`) is defined now; individual services become
runnable as later Milestone 1 issues add their Dockerfiles and application code.

Prerequisites: Docker with the Docker Compose plugin, and GNU Make.

Intended workflow:

```bash
git clone <repo-url>
cd community
cp .env.example .env   # adjust local values; never commit .env
make up                # start the development stack
make logs              # follow service logs
make down              # stop the stack
```

Other stable commands (`make test`, `make migrate`, `make seed`, ...) are
defined in the [Makefile](Makefile). Some delegate to tooling that arrives in
later milestone issues and currently print a short note indicating where that
behavior lands.

### Backend

The `api` service runs the FastAPI backend with hot reload in development.

- Liveness: `GET /health/live` returns `{"status": "alive"}` and never touches the database.
- Readiness: `GET /health/ready` returns `200` when PostgreSQL is reachable and `503` otherwise; it checks no external services.
- API docs: `/docs` (OpenAPI) are available in development and disabled in production.

Run backend checks through Compose: `make test-backend`, `make lint`,
`make format`. With `uv` installed locally you can also run `uv run pytest`
directly from `backend/`. `make test-backend` starts a healthy PostgreSQL and
creates the integration-test database automatically, so no `make up` is needed
first.

### Authentication

Sign-in uses GitHub OAuth with PostgreSQL-backed server-side sessions. The
browser holds only an opaque, HttpOnly session cookie; the database stores a
SHA-256 hash of the token.

Local setup:

1. Create a GitHub OAuth App (GitHub → Settings → Developer settings → OAuth Apps).
   - Homepage URL: `http://localhost:5173`
   - Authorization callback URL: `http://localhost:5173/api/auth/github/callback`
2. Put the client id/secret in your local `.env` (`GITHUB_OAUTH_CLIENT_ID`,
   `GITHUB_OAUTH_CLIENT_SECRET`). Never commit them.
3. `make up`, open `http://localhost:5173`, and click "Sign in with GitHub".

The frontend always calls the backend via same-origin `/api` paths. In
development, Vite proxies `/api` to the backend (`VITE_API_PROXY_TARGET`,
default `http://api:8000` for Docker; use `http://localhost:8000` for
host-based dev). **In production, a reverse proxy must serve the frontend and
backend under the same origin and route `/api` to the backend**, so the
`SameSite=Lax` session cookie remains first-party. Mutating requests must send
the double-submit CSRF token (from the readable CSRF cookie) in the
`X-CSRF-Token` header.

Authentication is optional for startup: health and non-auth routes work without
OAuth configured; auth endpoints return a clear error until credentials are set.

### Database

PostgreSQL schema changes are managed with Alembic.

- `make migrate` applies all migrations to `head` against the development database.
- `make migration name="description"` autogenerates a new revision.
- `make db-shell` opens an interactive `psql` shell in the running database.

Integration tests run against a separate `*_test` database on the same
PostgreSQL service, configured via `TEST_DATABASE_URL`; they never use SQLite
and refuse to run if `TEST_DATABASE_URL` resolves to the same database as
`DATABASE_URL`.

### Configuration

Deployment configuration is provided through environment variables.
`.env.example` holds safe development placeholders only; copy it to `.env` for
local use. Real `.env` files are git-ignored and must never be committed.

PostgreSQL 17 runs as the `db` service with a named persistent volume and is
**not** published to the host by default.
