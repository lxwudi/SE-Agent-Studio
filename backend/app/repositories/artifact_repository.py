from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Artifact, Project


class ArtifactRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_project_uid(self, project_uid: str, owner_id: int) -> list[Artifact]:
        stmt = (
            select(Artifact)
            .join(Project, Project.id == Artifact.project_id)
            .where(Project.uid == project_uid, Project.owner_id == owner_id)
            .order_by(Artifact.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_uid(self, artifact_uid: str, owner_id: int) -> Optional[Artifact]:
        stmt = (
            select(Artifact)
            .join(Project, Project.id == Artifact.project_id)
            .where(Artifact.artifact_uid == artifact_uid, Project.owner_id == owner_id)
        )
        return self.db.scalar(stmt)
