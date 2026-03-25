from __future__ import annotations

from sqlalchemy import Boolean
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.models.base import BIGINT_PK
from app.db.models.base import Base
from app.db.models.mixins import TimestampMixin


class AgentProfile(TimestampMixin, Base):
    __tablename__ = "agent_profile"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    agent_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    source_file: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    default_model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    allow_delegation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    prompt_versions = relationship(
        "PromptTemplateVersion",
        back_populates="agent_profile",
        cascade="all, delete-orphan",
    )


class PromptTemplateVersion(TimestampMixin, Base):
    __tablename__ = "prompt_template_version"

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True)
    agent_profile_id: Mapped[int] = mapped_column(ForeignKey("agent_profile.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    backstory_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rules_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)

    agent_profile = relationship("AgentProfile", back_populates="prompt_versions")

