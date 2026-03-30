from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.db.models import Artifact, FlowRun, Project, RunEvent, TaskRun


class RunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, flow_run: FlowRun) -> FlowRun:
        self.db.add(flow_run)
        self.db.commit()
        self.db.refresh(flow_run)
        return flow_run

    def get_run(self, run_uid: str, owner_id: int | None = None) -> Optional[FlowRun]:
        stmt = select(FlowRun).where(FlowRun.run_uid == run_uid)
        if owner_id is not None:
            stmt = stmt.join(Project, Project.id == FlowRun.project_id).where(Project.owner_id == owner_id)
        return self.db.scalar(stmt)

    def save_run(self, flow_run: FlowRun) -> FlowRun:
        self.db.add(flow_run)
        self.db.commit()
        self.db.refresh(flow_run)
        return flow_run

    def list_tasks(self, flow_run_id: int) -> list[TaskRun]:
        stmt = select(TaskRun).where(TaskRun.flow_run_id == flow_run_id).order_by(TaskRun.created_at)
        return list(self.db.scalars(stmt).all())

    def list_events(self, flow_run_id: int, since_id: int = 0) -> list[RunEvent]:
        stmt = (
            select(RunEvent)
            .where(RunEvent.flow_run_id == flow_run_id, RunEvent.id > since_id)
            .order_by(RunEvent.id)
        )
        return list(self.db.scalars(stmt).all())

    def create_task(self, task_run: TaskRun) -> TaskRun:
        self.db.add(task_run)
        self.db.commit()
        self.db.refresh(task_run)
        return task_run

    def save_task(self, task_run: TaskRun) -> TaskRun:
        self.db.add(task_run)
        self.db.commit()
        self.db.refresh(task_run)
        return task_run

    def create_event(self, run_event: RunEvent) -> RunEvent:
        self.db.add(run_event)
        self.db.commit()
        self.db.refresh(run_event)
        return run_event

    def create_artifact(self, artifact: Artifact) -> Artifact:
        self.db.add(artifact)
        self.db.commit()
        self.db.refresh(artifact)
        return artifact

    def finalize_open_tasks(self, flow_run_id: int, *, status: str, error_message: str = "") -> None:
        stmt = select(TaskRun).where(
            TaskRun.flow_run_id == flow_run_id,
            TaskRun.status.in_(("PENDING", "RUNNING")),
        )
        open_tasks = list(self.db.scalars(stmt).all())
        if not open_tasks:
            return

        finished_at = utc_now()
        for task in open_tasks:
            task.status = status
            task.finished_at = finished_at
            if error_message and not task.error_message:
                task.error_message = error_message
            self.db.add(task)
        self.db.commit()

    def clear_run_history(self, flow_run_id: int) -> None:
        self.db.execute(delete(RunEvent).where(RunEvent.flow_run_id == flow_run_id))
        self.db.execute(delete(Artifact).where(Artifact.flow_run_id == flow_run_id))
        self.db.execute(delete(TaskRun).where(TaskRun.flow_run_id == flow_run_id))
        self.db.commit()
