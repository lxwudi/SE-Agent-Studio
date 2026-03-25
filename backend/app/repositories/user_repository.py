from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalar(stmt)

    def get_by_uid(self, user_uid: str) -> Optional[User]:
        stmt = select(User).where(User.uid == user_uid)
        return self.db.scalar(stmt)

    def count(self) -> int:
        stmt = select(User)
        return len(list(self.db.scalars(stmt).all()))

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
