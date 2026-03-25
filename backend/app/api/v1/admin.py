from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.schemas.catalog import AgentProfileDetail, AgentProfilePatch, WorkflowTemplateDetail, WorkflowTemplatePatch
from app.services.catalog_service import CatalogService


router = APIRouter(dependencies=[Depends(get_admin_user)])


@router.get("/agents", response_model=list[AgentProfileDetail])
def list_agents(db: Session = Depends(get_db)) -> list[AgentProfileDetail]:
    return CatalogService(db).list_agents()


@router.patch("/agents/{agent_code}", response_model=AgentProfileDetail)
def update_agent(agent_code: str, payload: AgentProfilePatch, db: Session = Depends(get_db)) -> AgentProfileDetail:
    agent = CatalogService(db).update_agent(agent_code, payload)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


@router.get("/workflows", response_model=list[WorkflowTemplateDetail])
def list_workflows(db: Session = Depends(get_db)) -> list[WorkflowTemplateDetail]:
    return CatalogService(db).list_workflows()


@router.patch("/workflows/{workflow_code}", response_model=WorkflowTemplateDetail)
def update_workflow(
    workflow_code: str,
    payload: WorkflowTemplatePatch,
    db: Session = Depends(get_db),
) -> WorkflowTemplateDetail:
    workflow = CatalogService(db).update_workflow(workflow_code, payload)
    if not workflow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return workflow
