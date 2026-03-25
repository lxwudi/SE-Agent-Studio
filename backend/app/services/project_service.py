import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Project, User
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreateRequest, ProjectDetailResponse, ProjectResponse, ProjectUpdateRequest


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.repository = ProjectRepository(db)

    def create_project(self, user: User, payload: ProjectCreateRequest) -> ProjectDetailResponse:
        project = Project(
            uid=uuid.uuid4().hex,
            owner_id=user.id,
            name=payload.name,
            summary=payload.description,
            requirement_text=payload.latest_requirement,
            status="DRAFT",
            meta_json={},
        )
        return self._build_detail_response(self.repository.create(project))

    def list_projects(self, user: User) -> list[ProjectResponse]:
        return [ProjectResponse.model_validate(item) for item in self.repository.list(user.id)]

    def get_project(self, user: User, project_uid: str) -> Optional[ProjectDetailResponse]:
        project = self.repository.get_by_uid(project_uid, user.id)
        if not project:
            return None
        return self._build_detail_response(project)

    def update_project(self, user: User, project_uid: str, payload: ProjectUpdateRequest) -> Optional[ProjectDetailResponse]:
        project = self.repository.get_by_uid(project_uid, user.id)
        if not project:
            return None

        if payload.name is not None:
            project.name = payload.name
        if payload.description is not None:
            project.summary = payload.description
        if payload.latest_requirement is not None:
            project.requirement_text = payload.latest_requirement

        return self._build_detail_response(self.repository.save(project))

    def _build_detail_response(self, project: Project) -> ProjectDetailResponse:
        recent_run_uids = [run.run_uid for run in sorted(project.runs, key=lambda item: item.created_at, reverse=True)[:5]]
        return ProjectDetailResponse.model_validate(
            {
                "uid": project.uid,
                "name": project.name,
                "summary": project.summary,
                "requirement_text": project.requirement_text,
                "status": project.status,
                "created_at": project.created_at,
                "updated_at": project.updated_at,
                "recent_run_uids": recent_run_uids,
            }
        )
