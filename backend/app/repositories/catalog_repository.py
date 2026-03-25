from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import AgentProfile, PromptTemplateVersion, WorkflowTemplate


class CatalogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_agent_by_code(self, agent_code: str) -> Optional[AgentProfile]:
        stmt = (
            select(AgentProfile)
            .options(selectinload(AgentProfile.prompt_versions))
            .where(AgentProfile.agent_code == agent_code)
        )
        return self.db.scalar(stmt)

    def list_agents(self) -> list[AgentProfile]:
        stmt = select(AgentProfile).options(selectinload(AgentProfile.prompt_versions)).order_by(AgentProfile.display_name)
        return list(self.db.scalars(stmt).all())

    def list_workflows(self) -> list[WorkflowTemplate]:
        stmt = select(WorkflowTemplate).options(selectinload(WorkflowTemplate.steps)).order_by(WorkflowTemplate.name)
        return list(self.db.scalars(stmt).all())

    def get_workflow_by_code(self, workflow_code: str) -> Optional[WorkflowTemplate]:
        stmt = (
            select(WorkflowTemplate)
            .options(selectinload(WorkflowTemplate.steps))
            .where(WorkflowTemplate.workflow_code == workflow_code)
        )
        return self.db.scalar(stmt)

    def latest_prompt_version(self, agent_profile: AgentProfile) -> Optional[PromptTemplateVersion]:
        if not agent_profile.prompt_versions:
            return None
        return sorted(agent_profile.prompt_versions, key=lambda item: item.version)[-1]
