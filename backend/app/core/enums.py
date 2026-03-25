from __future__ import annotations

from enum import Enum


class FlowRunStatus(str, Enum):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    WAITING_REVIEW = "WAITING_REVIEW"
    PARTIAL_FAILED = "PARTIAL_FAILED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ArtifactType(str, Enum):
    REQUIREMENT_SPEC = "requirement_spec"
    ARCHITECTURE_BLUEPRINT = "architecture_blueprint"
    BACKEND_DESIGN = "backend_design"
    FRONTEND_BLUEPRINT = "frontend_blueprint"
    AI_INTEGRATION_SPEC = "ai_integration_spec"
    API_TEST_PLAN = "api_test_plan"
    CONSISTENCY_REVIEW = "consistency_review"

