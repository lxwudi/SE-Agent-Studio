from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.agent import AgentProfile
from app.db.models.workflow import WorkflowTemplate


class AdminRepository:
    @staticmethod
    def list_agents(session: Session) -> list[AgentProfile]:
        statement = select(AgentProfile).order_by(AgentProfile.display_name.asc())
        return list(session.scalars(statement).all())

    @staticmethod
    def get_agent(session: Session, agent_code: str) -> Optional[AgentProfile]:
        statement = select(AgentProfile).where(AgentProfile.agent_code == agent_code)
        return session.scalar(statement)

    @staticmethod
    def list_workflows(session: Session) -> list[WorkflowTemplate]:
        statement = select(WorkflowTemplate).order_by(WorkflowTemplate.name.asc())
        return list(session.scalars(statement).all())

    @staticmethod
    def get_workflow(session: Session, workflow_code: str) -> Optional[WorkflowTemplate]:
        statement = select(WorkflowTemplate).where(WorkflowTemplate.workflow_code == workflow_code)
        return session.scalar(statement)
