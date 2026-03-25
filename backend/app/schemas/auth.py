import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=200)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uid: str
    email: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: dt.datetime


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
