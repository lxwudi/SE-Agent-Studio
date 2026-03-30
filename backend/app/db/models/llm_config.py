from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utc_now
from app.db.session import Base


class UserLLMConfig(Base):
    __tablename__ = "user_llm_configs"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_llm_config_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider_name: Mapped[str] = mapped_column(String(120), default="OpenAI Compatible")
    base_url: Mapped[str] = mapped_column(String(255), default="https://api.openai.com/v1")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    default_model: Mapped[str] = mapped_column(String(120), default="")
    agent_model_overrides: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    agent_runtime_overrides: Mapped[dict[str, dict[str, object]]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="llm_config")
