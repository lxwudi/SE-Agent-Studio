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
    DELIVERY_REQUIREMENTS = "delivery_requirements"
    SOLUTION_DELIVERY_PLAN = "solution_delivery_plan"
    BACKEND_CODE_BUNDLE = "backend_code_bundle"
    FRONTEND_CODE_BUNDLE = "frontend_code_bundle"
    INTEGRATION_BUNDLE = "integration_bundle"
    DELIVERY_HANDOFF = "delivery_handoff"
