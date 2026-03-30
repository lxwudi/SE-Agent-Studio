import io
import re
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import FlowRun
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

    def delete_project(self, user: User, project_uid: str) -> bool:
        project = self.repository.get_by_uid(project_uid, user.id)
        if not project:
            return False

        self.repository.delete(project)
        return True

    def build_delivery_package(self, user: User, project_uid: str) -> Optional[tuple[str, bytes]]:
        project = self.repository.get_by_uid(project_uid, user.id)
        if not project:
            return None

        latest_delivery_run = self._find_latest_delivery_run(project)
        if latest_delivery_run is None:
            return None

        workspace_root = self._resolve_delivery_workspace(latest_delivery_run)
        if workspace_root is None or not workspace_root.exists() or not workspace_root.is_dir():
            return None

        package_name = self._build_package_basename(project.name, latest_delivery_run.run_uid)
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in sorted(workspace_root.rglob("*")):
                if not file_path.is_file():
                    continue
                relative_path = file_path.relative_to(workspace_root)
                archive.write(file_path, arcname=str(Path(package_name) / relative_path))

        return f"{package_name}.zip", archive_bytes.getvalue()

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

    def _find_latest_delivery_run(self, project: Project) -> Optional[FlowRun]:
        candidates = sorted(project.runs, key=lambda item: item.created_at, reverse=True)
        for run in candidates:
            if run.workflow_code != "delivery_v1":
                continue
            if run.status != "COMPLETED":
                continue
            if self._resolve_delivery_workspace(run) is not None:
                return run
        return None

    def _resolve_delivery_workspace(self, run: FlowRun) -> Optional[Path]:
        state_json = run.state_json if isinstance(run.state_json, dict) else {}
        handoff = state_json.get("delivery_handoff") if isinstance(state_json.get("delivery_handoff"), dict) else {}
        integration = (
            state_json.get("integration_bundle") if isinstance(state_json.get("integration_bundle"), dict) else {}
        )
        raw_path = handoff.get("workspace_root") or integration.get("workspace_root")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None

        workspace_root = Path(raw_path).expanduser().resolve()
        allowed_root = (settings.repo_root / ".delivery-workspaces").resolve()
        try:
            workspace_root.relative_to(allowed_root)
        except ValueError:
            return None
        return workspace_root

    def _build_package_basename(self, project_name: str, run_uid: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", project_name.strip()).strip("-").lower()
        if not slug:
            slug = "delivery-project"
        return f"{slug}-{run_uid[:8]}"
