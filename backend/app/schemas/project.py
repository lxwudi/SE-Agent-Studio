import datetime as dt
from typing import Any, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    summary: str = Field(default="", validation_alias=AliasChoices("summary", "description"))
    requirement_text: str = Field(default="", validation_alias=AliasChoices("requirement_text", "latest_requirement"))


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    summary: Optional[str] = None
    requirement_text: Optional[str] = None
    status: Optional[str] = None


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    uid: str
    name: str
    description: str = Field(validation_alias="summary")
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime


class ProjectDetail(ProjectListItem):
    latest_requirement: str = Field(validation_alias="requirement_text")
    meta_json: dict[str, Any]
    recent_run_uids: list[str] = Field(default_factory=list)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = ""
    latest_requirement: str = ""


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    latest_requirement: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    uid: str
    name: str
    description: str = Field(validation_alias="summary")
    latest_requirement: str = Field(validation_alias="requirement_text")
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime


class ProjectDetailResponse(ProjectResponse):
    recent_run_uids: list[str] = Field(default_factory=list)
