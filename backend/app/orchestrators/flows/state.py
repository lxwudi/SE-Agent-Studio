from __future__ import annotations

from typing import Optional
from typing import Any

from pydantic import BaseModel
from pydantic import Field


class ProjectFlowState(BaseModel):
    project_id: int
    flow_run_uid: str
    workflow_code: str
    requirement_text: str

    requirement_spec: Optional[dict[str, Any]] = None
    task_breakdown: Optional[dict[str, Any]] = None
    architecture_blueprint: Optional[dict[str, Any]] = None
    backend_design: Optional[dict[str, Any]] = None
    frontend_blueprint: Optional[dict[str, Any]] = None
    ai_integration_spec: Optional[dict[str, Any]] = None
    api_test_plan: Optional[dict[str, Any]] = None
    review_summary: Optional[dict[str, Any]] = None

    clarification_needed: bool = False
    review_required: bool = False
    current_stage: str = "created"
    artifact_ids: list[int] = Field(default_factory=list)
