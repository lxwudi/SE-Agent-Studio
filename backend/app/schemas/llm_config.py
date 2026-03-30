import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class AgentModelOption(BaseModel):
    agent_code: str
    display_name: str
    role_default_model: str
    enabled: bool
    override_enabled: bool = False
    provider_name: str = ""
    base_url: str = ""
    default_model: str = ""
    has_api_key: bool = False
    masked_api_key: str = ""
    is_ready: bool = False


class AgentRuntimeOverrideUpdate(BaseModel):
    override_enabled: bool = False
    provider_name: Optional[str] = Field(default=None, max_length=120)
    base_url: Optional[str] = Field(default=None, max_length=255)
    default_model: Optional[str] = Field(default=None, max_length=120)
    api_key: Optional[str] = Field(default=None, max_length=500)
    clear_api_key: bool = False


class UserLLMConfigUpdate(BaseModel):
    provider_name: Optional[str] = Field(default=None, max_length=120)
    base_url: Optional[str] = Field(default=None, max_length=255)
    default_model: Optional[str] = Field(default=None, max_length=120)
    agent_model_overrides: Optional[dict[str, str]] = None
    agent_overrides: Optional[dict[str, AgentRuntimeOverrideUpdate]] = None
    api_key: Optional[str] = Field(default=None, max_length=500)
    enabled: Optional[bool] = None
    clear_api_key: bool = False


class DiscoverModelsRequest(BaseModel):
    agent_code: Optional[str] = Field(default=None, max_length=120)
    provider_name: Optional[str] = Field(default=None, max_length=120)
    base_url: Optional[str] = Field(default=None, max_length=255)
    api_key: Optional[str] = Field(default=None, max_length=500)


class DiscoveredModelOption(BaseModel):
    model_id: str
    owned_by: Optional[str] = None


class DiscoverModelsResponse(BaseModel):
    provider_name: str
    base_url: str
    used_saved_api_key: bool
    models: list[DiscoveredModelOption] = Field(default_factory=list)


class UserLLMConfigResponse(BaseModel):
    provider_name: str
    base_url: str
    default_model: str
    enabled: bool
    has_api_key: bool
    masked_api_key: str
    agent_model_overrides: dict[str, str] = Field(default_factory=dict)
    available_roles: list[AgentModelOption] = Field(default_factory=list)
    is_ready: bool
    updated_at: Optional[dt.datetime] = None
