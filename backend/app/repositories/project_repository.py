from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def list(self, owner_id: int) -> list[Project]:
        stmt = select(Project).where(Project.owner_id == owner_id).order_by(Project.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def get_by_uid(self, project_uid: str, owner_id: int) -> Optional[Project]:
        stmt = select(Project).where(Project.uid == project_uid, Project.owner_id == owner_id)
        return self.db.scalar(stmt)

    def save(self, project: Project) -> Project:
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()
