from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectFlowState(BaseModel):
    id: Optional[str] = None
    project_id: int
    flow_run_uid: str
    workflow_code: str
    requirement_text: str
    requirement_spec: Optional[Dict[str, Any]] = None
    task_breakdown: Optional[Dict[str, Any]] = None
    architecture_blueprint: Optional[Dict[str, Any]] = None
    backend_design: Optional[Dict[str, Any]] = None
    frontend_blueprint: Optional[Dict[str, Any]] = None
    ai_integration_spec: Optional[Dict[str, Any]] = None
    api_test_plan: Optional[Dict[str, Any]] = None
    review_summary: Optional[Dict[str, Any]] = None
    clarification_needed: bool = False
    review_required: bool = False
    current_stage: str = "created"
    artifact_ids: List[int] = Field(default_factory=list)
