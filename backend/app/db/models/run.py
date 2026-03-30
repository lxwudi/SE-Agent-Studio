from __future__ import annotations

import datetime as dt
from typing import Any, List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.session import Base


class FlowRun(Base):
    __tablename__ = "flow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    workflow_template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("workflow_templates.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="CREATED", index=True)
    current_stage: Mapped[str] = mapped_column(String(120), default="created")
    input_requirement: Mapped[str] = mapped_column(Text, default="")
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    project: Mapped["Project"] = relationship(back_populates="runs")
    task_runs: Mapped[List["TaskRun"]] = relationship(back_populates="flow_run", cascade="all, delete-orphan")
    events: Mapped[List["RunEvent"]] = relationship(back_populates="flow_run", cascade="all, delete-orphan")
    artifacts: Mapped[List["Artifact"]] = relationship(back_populates="flow_run", cascade="all, delete-orphan")

    @property
    def workflow_code(self) -> str:
        if isinstance(self.state_json, dict):
            value = self.state_json.get("workflow_code")
            if isinstance(value, str):
                return value
        return ""


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    flow_run_id: Mapped[int] = mapped_column(ForeignKey("flow_runs.id", ondelete="CASCADE"), index=True)
    step_code: Mapped[str] = mapped_column(String(120), index=True)
    agent_code: Mapped[str] = mapped_column(String(120), default="")
    crew_name: Mapped[str] = mapped_column(String(120), default="")
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_text: Mapped[str] = mapped_column(Text, default="")
    prompt_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    token_usage_prompt: Mapped[int] = mapped_column(Integer, default=0)
    token_usage_completion: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(64), default="PENDING", index=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[dt.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    flow_run: Mapped["FlowRun"] = relationship(back_populates="task_runs")


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_run_id: Mapped[int] = mapped_column(ForeignKey("flow_runs.id", ondelete="CASCADE"), index=True)
    task_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task_runs.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120), index=True)
    event_source: Mapped[str] = mapped_column(String(120), default="")
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    flow_run: Mapped["FlowRun"] = relationship(back_populates="events")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    flow_run_id: Mapped[int] = mapped_column(ForeignKey("flow_runs.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    source_task_run_id: Mapped[Optional[int]] = mapped_column(ForeignKey("task_runs.id"), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="artifacts")
    flow_run: Mapped["FlowRun"] = relationship(back_populates="artifacts")
