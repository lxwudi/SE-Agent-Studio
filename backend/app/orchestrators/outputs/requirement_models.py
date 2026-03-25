from typing import List

from pydantic import BaseModel


class RequirementSpec(BaseModel):
    project_name: str
    problem_statement: str
    target_users: List[str]
    core_features: List[str]
    non_functional_requirements: List[str]
    constraints: List[str]
    assumptions: List[str]
    open_questions: List[str]


class TaskItem(BaseModel):
    title: str
    owner_role: str
    objective: str
    deliverable: str


class TaskBreakdown(BaseModel):
    milestones: List[TaskItem]
    priorities: List[str]
    clarification_list: List[str]


class RequirementsStageOutput(BaseModel):
    requirement_spec: RequirementSpec
    task_breakdown: TaskBreakdown
