import datetime as dt

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    status: str


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: str
    email: str
    display_name: str
    is_admin: bool
    created_at: dt.datetime
