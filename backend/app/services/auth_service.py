from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthTokenResponse, LoginRequest, UserResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repository = UserRepository(db)

    def authenticate(self, payload: LoginRequest) -> AuthTokenResponse:
        user = self.user_repository.get_by_email(payload.email)
        if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

        user.last_login_at = utc_now()
        self.user_repository.save(user)
        return self._build_token_response(user)

    def get_user_by_uid(self, user_uid: str) -> Optional[User]:
        return self.user_repository.get_by_uid(user_uid)

    def _build_token_response(self, user: User) -> AuthTokenResponse:
        return AuthTokenResponse(
            access_token=create_access_token(user.uid),
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        )
