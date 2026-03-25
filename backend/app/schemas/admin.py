from __future__ import annotations

from typing import Any
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMBaseModel


class AgentProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    default_model: Optional[str] = None
    temperature: Optional[float] = None
    allow_delegation: Optional[bool] = None
    enabled: Optional[bool] = None
    meta_json: Optional[dict[str, Any]] = None


class AgentProfileResponse(ORMBaseModel):
    agent_code: str
    display_name: str
    description: str
    source_file: str
    default_model: str
    temperature: float
    allow_delegation: bool
    enabled: bool
    meta_json: dict[str, Any]


class WorkflowTemplateUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    config_json: Optional[dict[str, Any]] = None


class WorkflowTemplateResponse(ORMBaseModel):
    workflow_code: str
    name: str
    description: str
    version: str
    enabled: bool
    config_json: dict[str, Any]
