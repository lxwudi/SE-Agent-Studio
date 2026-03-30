from __future__ import annotations

from celery.utils.log import get_task_logger

from app.core.config import settings
from app.services.run_service import execute_run_in_session
from app.workers.celery_app import celery_app


logger = get_task_logger(__name__)


@celery_app.task(
    name="run_technical_design_flow",
    bind=True,
    queue=settings.celery_task_queue,
    acks_late=True,
    reject_on_worker_lost=True,
)
def run_technical_design_flow(self, run_uid: str) -> None:  # type: ignore[no-untyped-def]
    logger.info("dispatching workflow run", extra={"run_uid": run_uid, "task_id": self.request.id})
    execute_run_in_session(run_uid, raise_on_failure=True)
