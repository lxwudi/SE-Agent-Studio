import datetime as dt
import uuid
from threading import Thread
from typing import Optional

from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.db.models import FlowRun, User
from app.db.session import session_scope
from app.orchestrators.flows.technical_design_flow import TechnicalDesignFlow
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.schemas.run import FlowRunResponse, RunCreate, RunEventResponse, RunTaskResponse


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
        flow_run = FlowRun(
            run_uid=uuid.uuid4().hex,
            project_id=project.id,
            workflow_template_id=workflow.id if workflow else None,
            status="QUEUED",
            current_stage="queued",
            input_requirement=payload.requirement_text,
            state_json={},
        )
        flow_run = self.run_repository.create_run(flow_run)
        project.requirement_text = payload.requirement_text
        project.status = "ACTIVE"
        self.project_repository.save(project)

        self.dispatch_run(flow_run.run_uid)
        return FlowRunResponse.model_validate(flow_run)

    def dispatch_run(self, run_uid: str) -> None:
        if settings.execution_mode == "celery":
            from app.workers.tasks import run_technical_design_flow

            run_technical_design_flow.delay(run_uid)
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
        if run.status in {"COMPLETED", "FAILED"}:
            return FlowRunResponse.model_validate(run)
        run.status = "CANCELLED"
        run.finished_at = utc_now()
        return FlowRunResponse.model_validate(self.run_repository.save_run(run))

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
        self.dispatch_run(run.run_uid)
        return FlowRunResponse.model_validate(run)


def execute_run_in_session(run_uid: str) -> None:
    with session_scope() as db:
        run_repository = RunRepository(db)
        flow_run = run_repository.get_run(run_uid)
        if not flow_run:
            return
        flow = TechnicalDesignFlow(db, flow_run)
        flow.run()
