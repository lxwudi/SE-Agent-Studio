from fastapi import APIRouter

from app.api.v1 import admin, artifacts, auth, llm_config, projects, runs, system


api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(llm_config.router, tags=["llm-config"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(runs.router, tags=["runs"])
api_router.include_router(artifacts.router, tags=["artifacts"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
