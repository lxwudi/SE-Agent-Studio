from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Artifact, User
from app.repositories.artifact_repository import ArtifactRepository
from app.schemas.artifact import ArtifactDetail, ArtifactListItem


class ArtifactService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ArtifactRepository(db)

    def list_artifacts(self, user: User, project_uid: str) -> list[ArtifactListItem]:
        return [ArtifactListItem.model_validate(item) for item in self.repository.list_by_project_uid(project_uid, user.id)]

    def get_artifact(self, user: User, artifact_uid: str) -> Optional[ArtifactDetail]:
        artifact = self.repository.get_by_uid(artifact_uid, user.id)
        if not artifact:
            return None
        return ArtifactDetail.model_validate(artifact)

    def get_artifact_model(self, user: User, artifact_uid: str) -> Optional[Artifact]:
        return self.repository.get_by_uid(artifact_uid, user.id)
