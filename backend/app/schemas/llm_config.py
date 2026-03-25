import datetime as dt
from typing import Optional

from pydantic import BaseModel, Field


class UserLLMConfigUpdate(BaseModel):
    provider_name: Optional[str] = Field(default=None, max_length=120)
    base_url: Optional[str] = Field(default=None, max_length=255)
    default_model: Optional[str] = Field(default=None, max_length=120)
    api_key: Optional[str] = Field(default=None, max_length=500)
    enabled: Optional[bool] = None
    clear_api_key: bool = False


class UserLLMConfigResponse(BaseModel):
    provider_name: str
    base_url: str
    default_model: str
    enabled: bool
    has_api_key: bool
    masked_api_key: str
    is_ready: bool
    updated_at: Optional[dt.datetime] = None
