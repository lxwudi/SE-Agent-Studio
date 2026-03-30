from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.project import ProjectCreateRequest, ProjectDetailResponse, ProjectResponse, ProjectUpdateRequest
from app.services.project_service import ProjectService


router = APIRouter(dependencies=[Depends(get_current_user)])


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetailResponse:
    return ProjectService(db).create_project(current_user, payload)


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProjectResponse]:
    return ProjectService(db).list_projects(current_user)


@router.get("/{project_uid}", response_model=ProjectDetailResponse)
def get_project(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetailResponse:
    project = ProjectService(db).get_project(current_user, project_uid)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_uid}", response_model=ProjectDetailResponse)
def update_project(
    project_uid: str,
    payload: ProjectUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProjectDetailResponse:
    project = ProjectService(db).update_project(current_user, project_uid, payload)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.delete("/{project_uid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    deleted = ProjectService(db).delete_project(current_user, project_uid)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_uid}/package")
def download_project_package(
    project_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    package = ProjectService(db).build_delivery_package(current_user, project_uid)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No downloadable delivery package found for this project.",
        )

    filename, content = package
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(BytesIO(content), media_type="application/zip", headers=headers)
