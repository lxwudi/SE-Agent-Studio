import datetime as dt
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    requirement_text: str = Field(min_length=10)
    workflow_code: str = Field(default="technical_design_v1")


class RunTaskItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_uid: str
    step_code: str
    agent_code: str
    crew_name: str
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    output_text: str
    status: str
    error_message: str
    created_at: dt.datetime
    updated_at: dt.datetime
    started_at: Optional[Union[dt.datetime, str]]
    finished_at: Optional[Union[dt.datetime, str]]


class RunEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    event_source: str
    payload_json: dict[str, Any]
    created_at: dt.datetime


class FlowRunDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_uid: str
    workflow_code: str
    status: str
    current_stage: str
    input_requirement: str
    state_json: dict[str, Any]
    error_message: str
    updated_at: dt.datetime
    started_at: Optional[Union[dt.datetime, str]]
    finished_at: Optional[Union[dt.datetime, str]]
    created_at: dt.datetime


class RunResumeResponse(BaseModel):
    message: str


class RunCreateRequest(RunCreate):
    pass


class RunTaskResponse(RunTaskItem):
    pass


class RunEventResponse(RunEventItem):
    pass


class FlowRunResponse(FlowRunDetail):
    pass
