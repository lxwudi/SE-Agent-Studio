from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


settings = get_settings()

celery_app = Celery(
    "se_agent_studio",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_track_started = True

