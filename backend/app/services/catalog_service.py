from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.catalog_repository import CatalogRepository
from app.schemas.catalog import AgentProfileDetail, AgentProfilePatch, WorkflowTemplateDetail, WorkflowTemplatePatch


class CatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = CatalogRepository(db)

    def list_agents(self) -> list[AgentProfileDetail]:
        return [AgentProfileDetail.model_validate(item) for item in self.repository.list_agents()]

    def update_agent(self, agent_code: str, payload: AgentProfilePatch) -> Optional[AgentProfileDetail]:
        agent = self.repository.get_agent_by_code(agent_code)
        if not agent:
            return None
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(agent, field, value)
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return AgentProfileDetail.model_validate(agent)

    def list_workflows(self) -> list[WorkflowTemplateDetail]:
        return [WorkflowTemplateDetail.model_validate(item) for item in self.repository.list_workflows()]

    def update_workflow(self, workflow_code: str, payload: WorkflowTemplatePatch) -> Optional[WorkflowTemplateDetail]:
        workflow = self.repository.get_workflow_by_code(workflow_code)
        if not workflow:
            return None
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(workflow, field, value)
        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return WorkflowTemplateDetail.model_validate(workflow)
