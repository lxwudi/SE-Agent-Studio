from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.run import FlowRun
from app.db.models.run import RunEvent
from app.db.models.run import TaskRun


class PlatformEventListener:
    def __init__(self, session: Session) -> None:
        self.session = session

    def emit(
        self,
        *,
        flow_run: FlowRun,
        event_type: str,
        event_source: str,
        payload_json: dict,
        task_run: Optional[TaskRun] = None,
    ) -> RunEvent:
        event = RunEvent(
            flow_run_id=flow_run.id,
            task_run_id=task_run.id if task_run else None,
            event_type=event_type,
            event_source=event_source,
            payload_json=payload_json,
        )
        self.session.add(event)
        self.session.flush()
        return event
