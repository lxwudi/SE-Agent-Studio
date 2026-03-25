import uuid
from threading import Thread
from typing import Optional

from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.db.models import FlowRun, RunEvent, User
from app.db.session import session_scope
from app.orchestrators.flows.technical_design_flow import TechnicalDesignFlow
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.schemas.run import FlowRunResponse, RunCreate, RunEventResponse, RunTaskResponse


class WorkflowNotFoundError(ValueError):
    def __init__(self, workflow_code: str):
        super().__init__(f"Workflow '{workflow_code}' not found.")
        self.workflow_code = workflow_code


class WorkflowDisabledError(ValueError):
    def __init__(self, workflow_code: str):
        super().__init__(f"Workflow '{workflow_code}' is disabled.")
        self.workflow_code = workflow_code


class WorkerDispatchError(RuntimeError):
    pass


class RunService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repository = ProjectRepository(db)
        self.run_repository = RunRepository(db)
        self.catalog_repository = CatalogRepository(db)

    def create_run(self, user: User, project_uid: str, payload: RunCreate) -> Optional[FlowRunResponse]:
        project = self.project_repository.get_by_uid(project_uid, user.id)
        if not project:
            return None

        workflow = self.catalog_repository.get_workflow_by_code(payload.workflow_code)
        if workflow is None:
            raise WorkflowNotFoundError(payload.workflow_code)
        if not workflow.enabled:
            raise WorkflowDisabledError(payload.workflow_code)

        flow_run = FlowRun(
            run_uid=uuid.uuid4().hex,
            project_id=project.id,
            workflow_template_id=workflow.id,
            status="QUEUED",
            current_stage="queued",
            input_requirement=payload.requirement_text,
            state_json={},
        )
        flow_run = self.run_repository.create_run(flow_run)
        project.requirement_text = payload.requirement_text
        project.status = "ACTIVE"
        self.project_repository.save(project)

        try:
            self.dispatch_run(flow_run.run_uid)
        except WorkerDispatchError as exc:
            mark_flow_run_failed(
                self.run_repository,
                flow_run,
                error_message=str(exc),
                event_type="flow.dispatch_failed",
                phase="dispatch",
            )
            raise

        return FlowRunResponse.model_validate(flow_run)

    def dispatch_run(self, run_uid: str) -> None:
        if settings.execution_mode == "celery":
            from kombu.exceptions import OperationalError

            from app.workers.tasks import run_technical_design_flow

            try:
                run_technical_design_flow.apply_async(
                    args=(run_uid,),
                    queue=settings.celery_task_queue,
                    retry=True,
                    retry_policy={
                        "max_retries": settings.celery_publish_retry_attempts,
                        "interval_start": 0,
                        "interval_step": 0.5,
                        "interval_max": 2,
                    },
                )
            except OperationalError as exc:
                raise WorkerDispatchError(
                    "无法把运行投递到 Celery Worker，请检查 Redis 和 Worker 进程是否可用。"
                ) from exc
            return

        worker = Thread(target=execute_run_in_session, args=(run_uid,), daemon=True)
        worker.start()

    def get_run(self, user: User, run_uid: str) -> Optional[FlowRunResponse]:
        run = self.run_repository.get_run(run_uid, user.id)
        if not run:
            return None
        return FlowRunResponse.model_validate(run)

    def list_tasks(self, user: User, run_uid: str) -> list[RunTaskResponse]:
        run = self.run_repository.get_run(run_uid, user.id)
        if not run:
            return []
        return [RunTaskResponse.model_validate(item) for item in self.run_repository.list_tasks(run.id)]

    def list_events(self, user: User, run_uid: str, since_id: int = 0) -> list[RunEventResponse]:
        run = self.run_repository.get_run(run_uid, user.id)
        if not run:
            return []
        return [RunEventResponse.model_validate(item) for item in self.run_repository.list_events(run.id, since_id=since_id)]

    def cancel_run(self, user: User, run_uid: str) -> Optional[FlowRunResponse]:
        run = self.run_repository.get_run(run_uid, user.id)
        if not run:
            return None
        if run.status in {"COMPLETED", "FAILED", "CANCELLED"}:
            return FlowRunResponse.model_validate(run)
        run.status = "CANCELLED"
        run.finished_at = utc_now()
        saved = self.run_repository.save_run(run)
        self.run_repository.create_event(
            RunEvent(
                flow_run_id=saved.id,
                event_type="flow.cancel_requested",
                event_source="RunService",
                payload_json={
                    "run_uid": saved.run_uid,
                    "current_stage": saved.current_stage,
                },
            )
        )
        return FlowRunResponse.model_validate(saved)

    def resume_run(self, user: User, run_uid: str) -> FlowRunResponse | bool | None:
        run = self.run_repository.get_run(run_uid, user.id)
        if not run:
            return None
        if run.status not in {"FAILED", "CANCELLED"}:
            return False

        run.status = "QUEUED"
        run.current_stage = "queued"
        run.error_message = ""
        run.finished_at = None
        run.started_at = None
        run.state_json = {}
        self.run_repository.save_run(run)
        try:
            self.dispatch_run(run.run_uid)
        except WorkerDispatchError as exc:
            mark_flow_run_failed(
                self.run_repository,
                run,
                error_message=str(exc),
                event_type="flow.dispatch_failed",
                phase="dispatch",
            )
            raise
        return FlowRunResponse.model_validate(run)


def mark_flow_run_failed(
    run_repository: RunRepository,
    flow_run: FlowRun,
    *,
    error_message: str,
    event_type: str = "flow.failed",
    phase: str = "execution",
) -> None:
    flow_run.status = "FAILED"
    flow_run.error_message = error_message
    flow_run.finished_at = utc_now()
    run_repository.save_run(flow_run)
    run_repository.create_event(
        RunEvent(
            flow_run_id=flow_run.id,
            event_type=event_type,
            event_source="TechnicalDesignFlow",
            payload_json={
                "error": error_message,
                "phase": phase,
            },
        )
    )


def execute_run_in_session(run_uid: str, *, raise_on_failure: bool = False) -> None:
    with session_scope() as db:
        run_repository = RunRepository(db)
        flow_run = run_repository.get_run(run_uid)
        if not flow_run:
            return
        try:
            flow = TechnicalDesignFlow(db, flow_run)
            flow.run()
        except Exception as exc:
            db.refresh(flow_run)
            if flow_run.status == "CANCELLED":
                return
            mark_flow_run_failed(
                run_repository,
                flow_run,
                error_message=str(exc),
                phase="execution",
            )
            if raise_on_failure:
                raise
