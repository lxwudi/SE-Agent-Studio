# SE-Agent Studio Backend

FastAPI backend for the first development phase of SE-Agent Studio.

## Stack

- `uv` for Python dependency management
- FastAPI for REST and SSE endpoints
- SQLAlchemy 2.x for persistence
- Celery + Redis as the planned async runtime
- Optional local `crewai` source dependency for the AI orchestration layer

## Quick Start Without Redis Or MySQL

本地开发推荐直接使用：

- `SQLite`
- `EXECUTION_MODE=thread`

这意味着你不需要先启动 `MySQL`、`Redis` 或 `Celery worker`。

### 1. Prepare `.env`

```bash
cp .env.example .env
```

把 `.env` 里至少改成：

```env
DATABASE_URL=sqlite:///./.runtime/se_agent_studio.db
EXECUTION_MODE=thread
AGENT_RUNTIME_MODE=auto
```

### 2. Start Backend

```bash
uv sync --extra ai-runtime --dev
uv run alembic upgrade head
uv run python scripts/bootstrap_data.py
uv run uvicorn app.main:app --reload
```

## Runtime Notes

- `.env.example` 里展示的是生产偏向的 `MySQL + Redis + Celery` 形态，但本地开发不需要按那个方式启动。
- 本地最省事的方式是 `DATABASE_URL=sqlite:///./.runtime/se_agent_studio.db`。
- 本地最省事的执行方式是 `EXECUTION_MODE=thread`，这样不会依赖 Redis / Celery。
- Alembic migration files live in `backend/alembic/`.
- Run execution currently supports a local background-thread mode and a Celery dispatch mode.
- Authentication is token-based and uses the bootstrap admin defined by `DEFAULT_OWNER_EMAIL` / `DEFAULT_OWNER_PASSWORD`.

## Optional Celery Mode

只有在你明确要跑队列模式时，才需要：

- MySQL
- Redis
- `EXECUTION_MODE=celery`
- 独立的 `celery worker`

## Smoke Test

```bash
pytest tests/test_api_smoke.py
```
