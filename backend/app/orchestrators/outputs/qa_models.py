from typing import List

from pydantic import BaseModel


class TestScenario(BaseModel):
    title: str
    category: str
    expected_result: str


class ApiTestPlan(BaseModel):
    coverage_focus: List[str]
    core_scenarios: List[TestScenario]
    acceptance_criteria: List[str]
    risk_checklist: List[str]


class ConsistencyReviewSummary(BaseModel):
    coherence_score: int
    aligned_areas: List[str]
    conflicts: List[str]
    next_actions: List[str]
