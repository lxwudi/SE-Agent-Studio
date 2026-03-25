from __future__ import annotations

from typing import Optional

from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.core.enums import ArtifactType
from app.core.security import generate_uid
from app.db.models.base import BIGINT_PK
from app.db.models.base import Base
from app.db.models.mixins import TimestampMixin


class Artifact(TimestampMixin, Base):
    __tablename__ = "artifact"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    artifact_uid: Mapped[str] = mapped_column(
        String(32),
        default=generate_uid,
        unique=True,
        index=True,
    )
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"), nullable=False)
    flow_run_id: Mapped[int] = mapped_column(ForeignKey("flow_run.id"), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    source_task_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("task_run.id"),
        default=None,
    )
    version_no: Mapped[int] = mapped_column(default=1, nullable=False)

    project = relationship("Project", back_populates="artifacts")
    flow_run = relationship("FlowRun", back_populates="artifacts")
    source_task_run = relationship("TaskRun", back_populates="artifacts")
    versions = relationship(
        "ArtifactVersion",
        back_populates="artifact",
        cascade="all, delete-orphan",
    )


class ArtifactVersion(TimestampMixin, Base):
    __tablename__ = "artifact_version"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    artifact_id: Mapped[int] = mapped_column(ForeignKey("artifact.id"), nullable=False)
    version_no: Mapped[int] = mapped_column(nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, default="", nullable=False)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    artifact = relationship("Artifact", back_populates="versions")
