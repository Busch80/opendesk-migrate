# opendesk-migrate

Multi-tenant migration tool: Microsoft 365 → openDesk (Mail, Calendar, Contacts, OneDrive).

> ⚠️ Pre-alpha. The skeleton runs and ships Alembic migrations and a UI shell.
> Real Graph/IMAP/CalDAV/WebDAV wiring lands with the credentials-based phases.

## Architecture

```
React (web) ──▶ FastAPI (api) ──▶ PostgreSQL (state + audit)
                  │
                  └─▶ Celery workers (mail | calendar | contacts | onedrive | maintenance)
                        │
                        └─▶ Redis (broker + cache)
                              │
                              └─▶ Named Docker volume "staging" (local FS, drop-in S3 later)
```

See `docs/ARCHITECTURE.md` for the full picture.

## Quick start (development)

### Prerequisites
- Docker 24+ with Compose v2
- Python 3.12+ (if running locally)
- Node 22+ (if running locally)

### Run via Docker Compose

```bash
cp .env.example .env
# Generate a Fernet key
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' \
    | (echo "FERNET_KEY=" && cat) >> .env
# Generate a SECRET_KEY
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' \
    | (echo "SECRET_KEY=" && cat) >> .env
# Set a Postgres password
echo "POSTGRES_PASSWORD=devpass" >> .env

docker compose up --build
```

Then open `http://localhost:8080` for the UI.
API at `http://localhost:8080/api/v1`, metrics at `http://localhost:8080/metrics`.

### Local development (without Docker)

```bash
# API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env  # then set FERNET_KEY, SECRET_KEY, DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
celery -A app.celery_init:celery worker -Q mail -l info  # in another shell
celery -A app.celery_init:celery beat -l info            # in another shell

# Web
cd web
npm install
npm run dev  # http://localhost:5173
```

## Repo layout

```
api/          FastAPI + SQLAlchemy 2.0 (async) + Celery
   ├── app/
   │   ├── config.py          # Pydantic Settings
   │   ├── db.py              # async engine + session
   │   ├── models.py          # SQLAlchemy ORM
   │   ├── schemas/           # Pydantic request/response
   │   ├── services/
   │   │   ├── encryption/    # Fernet wrapper
   │   │   ├── storage/       # local + s3 backend (S3 = future)
   │   │   ├── m365/          # Graph API client + tokens
   │   │   └── opendesk/      # OX + Nextcloud adapters
   │   ├── routers/           # FastAPI routers
   │   ├── tasks/             # Celery tasks
   │   ├── celery_init.py     # Celery app
   │   └── main.py            # FastAPI app factory
   ├── alembic/               # DB migrations
   ├── tests/
   ├── pyproject.toml
   └── Dockerfile

web/          React 19 + Vite + Tailwind + shadcn-style ui + i18next
   ├── src/
   │   ├── components/
   │   ├── pages/
   │   ├── i18n/locales/      # de/fr/it/en
   │   └── lib/
   ├── nginx.conf
   └── Dockerfile

ops/          Prometheus config, Postgres init scripts
docs/         ARCHITECTURE.md, ADRs, OPERATOR.md, RUNBOOK.md, SECURITY.md
.github/      GitHub Actions
docker-compose.yml
```

## Development commands

See `Makefile` — `make help`.

```bash
make lint          # ruff + mypy
make test          # pytest with coverage
make migration     # generate Alembic migration
make upgrade       # apply migrations
make dev           # start everything in Docker
make shell-api     # open shell in api container
make logs          # tail logs
make seed          # create demo tenant + users
```

## CI / GitHub Actions

Three workflow files are pre-configured under `.github/workflows/`:

- `backend.yml` — ruff, mypy, pytest with Postgres + Redis services
- `frontend.yml` — eslint, tsc, vite build, vitest
- `docker.yml` — image build & push to ghcr.io on `main` and tags

To activate CI, your repository admin must grant the `workflow` OAuth
scope to the GitHub PAT used by the deploy tool. Until then, workflows
exist locally but are not uploaded to GitHub.

```
# Once granted the scope, push them with:
git push origin HEAD:main
```

## Documentation

| Doc | Purpose |
|---|---|
| `docs/ARCHITECTURE.md` | Detailed system architecture |
| `docs/ADR/` | Architecture Decision Records |
| `docs/OPERATOR.md` | Day-2 operations runbook |
| `docs/RUNBOOK.md` | Incident response procedures |
| `docs/SECURITY.md` | Security architecture & incident reporting |
| `docs/COMPLIANCE.md` | CH-DSG / FINMA / AGPL notes |
| `docs/USER-GUIDE.md` | End-user instructions (consent flow) |

## Contributing

We follow the contributor workflow documented in `CONTRIBUTING.md`.
By submitting code you agree to AGPL-3.0-or-later terms.

## License

AGPL-3.0-or-later — see `LICENSE`.
