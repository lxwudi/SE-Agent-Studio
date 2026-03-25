from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import create_all_tables, session_scope
from app.services.bootstrap_service import bootstrap_catalog


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    if settings.auto_create_schema:
        create_all_tables()
    if settings.bootstrap_data_on_startup:
        with session_scope() as db:
            bootstrap_catalog(db)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
