from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import FlowRun
from app.orchestrators.flows.delivery_flow import DeliveryFlow
from app.orchestrators.flows.technical_design_flow import TechnicalDesignFlow
from app.repositories.catalog_repository import CatalogRepository


FLOW_RUNNERS = {
    "technical_design_v1": TechnicalDesignFlow,
    "delivery_v1": DeliveryFlow,
}


def resolve_workflow_code(db: Session, flow_run: FlowRun) -> str:
    workflow_code = flow_run.workflow_code
    if workflow_code:
        return workflow_code
    if flow_run.workflow_template_id:
        workflow = CatalogRepository(db).get_workflow_by_id(flow_run.workflow_template_id)
        if workflow:
            return workflow.workflow_code
    return ""


def resolve_flow_runner(db: Session, flow_run: FlowRun):
    workflow_code = resolve_workflow_code(db, flow_run)
    runner = FLOW_RUNNERS.get(workflow_code)
    if runner is None:
        raise ValueError(f"Workflow '{workflow_code or flow_run.workflow_template_id}' 当前没有对应的执行器。")
    return runner


def create_flow_runner(db: Session, flow_run: FlowRun):
    runner = resolve_flow_runner(db, flow_run)
    return runner(db, flow_run)


def resolve_flow_event_source(db: Session, flow_run: FlowRun) -> str:
    runner = resolve_flow_runner(db, flow_run)
    return runner.flow_event_source
