# community

Community and contributor management platform for omegaUp.

A standalone platform for managing and supporting omegaUp contributors across
programs such as Google Summer of Code, internships, school residencies, and
volunteer initiatives. It complements GitHub and omegaUp rather than replacing
either: GitHub stays the source of truth for contribution work, and omegaUp
stays the source of truth for contest/test activity.

## Documentation

- [Product design](docs/product-design.md) — product scope, concepts, workflows, and the three product areas (personal dashboard, programs, administration).
- [Technical design](docs/technical-design.md) — architecture, stack, and repository shape.
- [Milestone 1](docs/milestone-1.md) — foundation and first-edition plan.
- [Feature backlog](docs/feature-backlog.md) — lightweight, non-committal idea backlog.
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

### Authorization and superadmin bootstrap

Platform roles are stored in the database (`platform_roles`); the only role at
this stage is `superadmin`. Authorization is enforced server-side (admin
endpoints return `401` when anonymous and `403` for authenticated non-admins);
frontend route guards are a UX convenience only.

To grant the initial superadmin:

1. The target user signs in with GitHub at least once (so their Person and
   verified GitHub identity exist).
2. Find their immutable GitHub numeric id: `https://api.github.com/users/<login>`.
3. Add it to `SUPERADMIN_GITHUB_IDS` in your local `.env` (comma-separated for
   multiple). Use numeric ids, never usernames.
4. Run `make bootstrap-admins`.

The command is idempotent and safe to rerun: it grants the role only to the
configured ids, skips ids that have not signed in yet, and never modifies other
roles or users.

### Seeding the standard program catalog

A fresh installation should have the standard program catalog available without
manual data entry. Run:

```bash
make seed
```

This runs the version-controlled seed runner, which applies any pending seeds
that have not yet executed. The standard-catalog seed (`standard_catalog_v1`)
ensures the four standard programs (Google Summer of Code, Professional
Internships, Professional Residencies, Volunteering) and their initial 2026
editions exist:

| Program                   | Slug           | Editions          |
| ------------------------- | -------------- | ----------------- |
| Google Summer of Code     | `gsoc`         | `2026` (annual)   |
| Professional Internships  | `internships`  | `2026-1`, `2026-2`|
| Professional Residencies  | `residencies`  | `2026-1`, `2026-2`|
| Volunteering              | `volunteering` | `2026` (annual)   |

**A seed is not a database reset mechanism.** `make seed` is safe to rerun and
never deletes anything: it inserts only what is missing and never overwrites
administrator-edited names, descriptions, icons, or dates. These are
administrative containers only — no participants, mentors, or projects are
created.

Execution is tracked once per seed in a `seed_executions` table. A seed that has
already executed is a no-op on later runs, so a standard program an administrator
later deletes is **not** silently recreated. Each run takes a PostgreSQL
transaction-level advisory lock and commits its data together with its execution
record, so concurrent `make seed` invocations are safe and a failure rolls the
whole run back (leaving nothing recorded, so it can be retried).

Edition status is a temporal value computed from the edition's dates against the
current UTC date (`upcoming`/`active`/`finished`); it is not stored or set
manually.

### Deleting programs and editions

Superadmins can delete programs and editions from the administration UI (a
discreet Delete action on each program row, the program detail screen, and the
edition detail screen) or via the admin API. Deletion is **empty-only** and
enforced in the backend inside a transaction:

- A program can be deleted only when it has **no editions** (standard programs
  included — there is no special permanent-protection rule; an empty standard
  program is deletable).
- An edition can be deleted only when it has **no projects, participants, or
  mentors**.

Attempting to delete a non-empty program/edition returns `409 Conflict` and the
UI shows the reason. Deletion never cascades business data. Because deletion is
tracked against the once-only seed execution record above, a deleted standard
program stays deleted even if `make seed` runs again.

### Development-only data cleanup

Early development left a couple of obsolete program rows behind. A **dev-only**,
tightly-scoped cleanup command can remove exactly those known records
(slugs `2026` and `internship`) and nothing else:

```bash
# Inspect what would be removed (default: dry run, deletes nothing)
docker compose exec api python -m app.cli.cleanup_dev_programs

# Actually delete, after reviewing the report
docker compose exec api python -m app.cli.cleanup_dev_programs --confirm
```

This command is a controlled maintenance tool, not part of normal operation. It
only ever targets the exact obsolete slugs, refuses to touch standard programs,
refuses to delete anything that has dependent business data, defaults to a dry
run, and requires `--confirm` to act. It must never run automatically — not at
startup, not in migrations, and not during deployment.

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

### User interface language

All user-facing interface text is in English. There is no internationalization
(i18n) framework yet; UI strings live inline in the Vue components and are kept
reasonably organized. Introducing i18n infrastructure is a future decision, not
a Milestone 1 concern.
