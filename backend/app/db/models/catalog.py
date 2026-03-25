from __future__ import annotations

import datetime as dt
from typing import Any, List, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.session import Base


class AgentProfile(Base):
    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    source_file: Mapped[str] = mapped_column(String(255))
    default_model: Mapped[str] = mapped_column(String(120), default="")
    temperature: Mapped[float] = mapped_column(Float, default=0.2)
    allow_delegation: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    meta_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    prompt_versions: Mapped[List["PromptTemplateVersion"]] = relationship(
        back_populates="agent_profile",
        cascade="all, delete-orphan",
        order_by="PromptTemplateVersion.version",
    )


class PromptTemplateVersion(Base):
    __tablename__ = "prompt_template_versions"
    __table_args__ = (
        UniqueConstraint("agent_profile_id", "version", name="uq_prompt_template_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_profile_id: Mapped[int] = mapped_column(ForeignKey("agent_profiles.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    backstory_prompt: Mapped[str] = mapped_column(Text, default="")
    rules_prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    agent_profile: Mapped["AgentProfile"] = relationship(back_populates="prompt_versions")


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    steps: Mapped[List["WorkflowStep"]] = relationship(
        back_populates="workflow_template",
        cascade="all, delete-orphan",
        order_by="WorkflowStep.sort_order",
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        UniqueConstraint("workflow_template_id", "step_code", name="uq_workflow_step_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_template_id: Mapped[int] = mapped_column(ForeignKey("workflow_templates.id", ondelete="CASCADE"))
    step_code: Mapped[str] = mapped_column(String(120), index=True)
    step_type: Mapped[str] = mapped_column(String(120))
    agent_code: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    depends_on: Mapped[list[str]] = mapped_column(JSON, default=list)
    parallel_group: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    output_schema: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    workflow_template: Mapped["WorkflowTemplate"] = relationship(back_populates="steps")
