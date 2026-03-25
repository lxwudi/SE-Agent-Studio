from __future__ import annotations

from pydantic import BaseModel


class ConsistencyReviewSummary(BaseModel):
    overall_status: str
    aligned_points: list[str]
    review_actions: list[str]
    next_steps: list[str]

