import datetime as dt
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PromptTemplateVersionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    version: int
    system_prompt: str
    backstory_prompt: str
    rules_prompt: str
    created_at: dt.datetime


class AgentProfileDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_code: str
    display_name: str
    description: str
    source_file: str
    default_model: str
    temperature: float
    allow_delegation: bool
    enabled: bool
    meta_json: dict[str, Any]
    prompt_versions: list[PromptTemplateVersionItem]


class AgentProfilePatch(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    default_model: Optional[str] = None
    temperature: Optional[float] = None
    allow_delegation: Optional[bool] = None
    enabled: Optional[bool] = None


class WorkflowStepItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_code: str
    step_type: str
    agent_code: Optional[str]
    depends_on: list[str]
    parallel_group: Optional[str]
    output_schema: Optional[str]
    sort_order: int


class WorkflowStepPatch(BaseModel):
    step_code: str
    step_type: str
    agent_code: Optional[str] = None
    depends_on: list[str] = Field(default_factory=list)
    parallel_group: Optional[str] = None
    output_schema: Optional[str] = None
    sort_order: int


class WorkflowTemplateDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workflow_code: str
    name: str
    description: str
    version: int
    enabled: bool
    config_json: dict[str, Any]
    steps: list[WorkflowStepItem]


class WorkflowTemplatePatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    config_json: Optional[dict[str, Any]] = None
    steps: Optional[list[WorkflowStepPatch]] = None
