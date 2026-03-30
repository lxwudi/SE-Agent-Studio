from typing import List

from pydantic import BaseModel


class CommandSpec(BaseModel):
    label: str
    command: str
    purpose: str


class GeneratedFile(BaseModel):
    path: str
    language: str
    purpose: str
    content: str


class DeliveryRequirementSpec(BaseModel):
    app_name: str
    app_summary: str
    target_users: List[str]
    core_capabilities: List[str]
    acceptance_criteria: List[str]
    non_goals: List[str]


class SolutionDeliveryPlan(BaseModel):
    architecture_style: str
    stack_choices: List[str]
    workspace_layout: List[str]
    implementation_order: List[str]
    run_commands: List[CommandSpec]
    validation_commands: List[CommandSpec]
    delivery_notes: List[str]


class CodeBundle(BaseModel):
    bundle_name: str
    summary: str
    runtime: str
    entrypoints: List[str]
    files: List[GeneratedFile]
    run_commands: List[CommandSpec]
    setup_notes: List[str]


class VerificationResult(BaseModel):
    label: str
    command: str
    success: bool
    exit_code: int
    summary: str
    output: str


class IntegrationBundle(BaseModel):
    workspace_root: str
    generated_files: List[str]
    files: List[GeneratedFile]
    startup_steps: List[str]
    verification_steps: List[str]
    verification_results: List[VerificationResult]
    exposed_endpoints: List[str]
    notes: List[str]


class DeliveryHandoff(BaseModel):
    workspace_root: str
    generated_assets: List[str]
    startup_guide: List[str]
    verification_status: List[str]
    verification_results: List[VerificationResult]
    next_steps: List[str]
