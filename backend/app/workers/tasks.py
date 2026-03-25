from __future__ import annotations

from app.services.run_service import execute_run_in_session
from app.workers.celery_app import celery_app


@celery_app.task(name="run_technical_design_flow")
def run_technical_design_flow(run_uid: str) -> None:
    execute_run_in_session(run_uid)
