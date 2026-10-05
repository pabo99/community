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

### Configuration

Deployment configuration is provided through environment variables.
`.env.example` holds safe development placeholders only; copy it to `.env` for
local use. Real `.env` files are git-ignored and must never be committed.

PostgreSQL 17 runs as the `db` service with a named persistent volume and is
**not** published to the host by default.
