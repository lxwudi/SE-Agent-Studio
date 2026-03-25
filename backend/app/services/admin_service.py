from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.admin_repository import AdminRepository
from app.schemas.admin import AgentProfileUpdateRequest
from app.schemas.admin import WorkflowTemplateUpdateRequest


class AdminService:
    @staticmethod
    def list_agents(session: Session):
        return AdminRepository.list_agents(session)

    @staticmethod
    def update_agent(session: Session, agent_code: str, payload: AgentProfileUpdateRequest):
        agent = AdminRepository.get_agent(session, agent_code)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found.")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(agent, key, value)
        session.flush()
        return agent

    @staticmethod
    def list_workflows(session: Session):
        return AdminRepository.list_workflows(session)

    @staticmethod
    def update_workflow(
        session: Session,
        workflow_code: str,
        payload: WorkflowTemplateUpdateRequest,
    ):
        workflow = AdminRepository.get_workflow(session, workflow_code)
        if workflow is None:
            raise HTTPException(status_code=404, detail="Workflow not found.")
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(workflow, key, value)
        session.flush()
        return workflow

