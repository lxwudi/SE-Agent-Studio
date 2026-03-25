from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.projects import router as projects_router
from app.api.v1.runs import router as runs_router


api_router = APIRouter()
api_router.include_router(projects_router)
api_router.include_router(runs_router)
api_router.include_router(artifacts_router)
api_router.include_router(admin_router)

