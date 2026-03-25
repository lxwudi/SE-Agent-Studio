from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import WorkflowStep
from app.repositories.catalog_repository import CatalogRepository
from app.schemas.catalog import AgentProfileDetail, AgentProfilePatch, WorkflowTemplateDetail, WorkflowTemplatePatch


class InvalidWorkflowTemplateError(ValueError):
    pass


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
        updates = payload.model_dump(exclude_none=True)
        steps = updates.pop("steps", None)

        for field, value in updates.items():
            setattr(workflow, field, value)

        if steps is not None:
            self._replace_workflow_steps(workflow, steps)

        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)
        return WorkflowTemplateDetail.model_validate(workflow)

    def _replace_workflow_steps(self, workflow, steps: list[dict]) -> None:
        if not steps:
            raise InvalidWorkflowTemplateError("Workflow 至少需要保留一个步骤。")

        step_codes = [item["step_code"] for item in steps]
        if len(step_codes) != len(set(step_codes)):
            raise InvalidWorkflowTemplateError("Workflow 中存在重复的 step_code。")

        for item in steps:
            if item["step_type"] != "crew":
                raise InvalidWorkflowTemplateError("当前版本仅支持 crew 类型的 workflow step。")

        workflow.steps.clear()
        self.db.flush()

        for item in sorted(steps, key=lambda value: value["sort_order"]):
            workflow.steps.append(
                WorkflowStep(
                    step_code=item["step_code"],
                    step_type=item["step_type"],
                    agent_code=item.get("agent_code"),
                    depends_on=item.get("depends_on") or [],
                    parallel_group=item.get("parallel_group"),
                    output_schema=item.get("output_schema"),
                    sort_order=item["sort_order"],
                )
            )
