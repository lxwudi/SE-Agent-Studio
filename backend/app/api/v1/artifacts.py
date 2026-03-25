from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.artifact import ArtifactDetail, ArtifactListItem
from app.services.artifact_service import ArtifactService


router = APIRouter()


@router.get("/projects/{project_uid}/artifacts", response_model=list[ArtifactListItem])
def list_project_artifacts(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ArtifactListItem]:
    return ArtifactService(db).list_artifacts(current_user, project_uid)


@router.get("/artifacts/{artifact_uid}", response_model=ArtifactDetail)
def get_artifact(
    artifact_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ArtifactDetail:
    artifact = ArtifactService(db).get_artifact(current_user, artifact_uid)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@router.get("/artifacts/{artifact_uid}/export")
def export_artifact(
    artifact_uid: str,
    format: Annotated[str, Query(pattern="^(md|pdf)$")] = "md",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PlainTextResponse:
    artifact = ArtifactService(db).get_artifact_model(current_user, artifact_uid)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    if format == "pdf":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export is planned for the next milestone.",
        )
    filename = f"{artifact.title or artifact.artifact_type}.md"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return PlainTextResponse(content=artifact.content_markdown or "", headers=headers)
