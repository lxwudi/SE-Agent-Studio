# SE-Agent Studio Backend

FastAPI backend for the first development phase of SE-Agent Studio.

## Stack

- `uv` for Python dependency management
- FastAPI for REST and SSE endpoints
- SQLAlchemy 2.x for persistence
- Celery + Redis as the planned async runtime
- Optional local `crewai` source dependency for the AI orchestration layer

## Quick Start

```bash
cp .env.example .env
uv sync --extra ai-runtime --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Runtime Notes

- Production database example is MySQL; local development can still switch to SQLite via `DATABASE_URL`.
- Alembic migration files live in `backend/alembic/`.
- Run execution currently supports a local background-thread mode and a Celery dispatch mode.
- Authentication is token-based and uses the bootstrap admin defined by `DEFAULT_OWNER_EMAIL` / `DEFAULT_OWNER_PASSWORD`.

## Smoke Test

```bash
pytest tests/test_api_smoke.py
```
