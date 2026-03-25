from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import UserLLMConfig


class LLMConfigRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[UserLLMConfig]:
        stmt = select(UserLLMConfig).where(UserLLMConfig.user_id == user_id)
        return self.db.scalar(stmt)

    def save(self, config: UserLLMConfig) -> UserLLMConfig:
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config
