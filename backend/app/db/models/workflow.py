from __future__ import annotations

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.models.base import BIGINT_PK
from app.db.models.base import Base
from app.db.models.mixins import TimestampMixin


class WorkflowTemplate(TimestampMixin, Base):
    __tablename__ = "workflow_template"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    workflow_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    steps = relationship(
        "WorkflowStep",
        back_populates="workflow_template",
        cascade="all, delete-orphan",
    )
    flow_runs = relationship("FlowRun", back_populates="workflow_template")


class WorkflowStep(TimestampMixin, Base):
    __tablename__ = "workflow_step"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    workflow_template_id: Mapped[int] = mapped_column(
        ForeignKey("workflow_template.id"),
        nullable=False,
    )
    step_code: Mapped[str] = mapped_column(String(80), nullable=False)
    step_type: Mapped[str] = mapped_column(String(40), default="crew", nullable=False)
    agent_code: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    depends_on: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    parallel_group: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    output_schema: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    workflow_template = relationship("WorkflowTemplate", back_populates="steps")

