import datetime as dt
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.db.models import Artifact, FlowRun, RunEvent, TaskRun, WorkflowTemplate
from app.orchestrators.agents.agent_factory import AgentFactory, ResolvedAgentProfile
from app.orchestrators.guardrails.architecture_guardrails import validate_architecture_blueprint
from app.orchestrators.guardrails.requirement_guardrails import validate_requirement_spec
from app.orchestrators.outputs.ai_models import AIIntegrationSpec
from app.orchestrators.outputs.architecture_models import ADRItem, ArchitectureBlueprint
from app.orchestrators.outputs.backend_models import ApiEndpointContract, BackendDesign, EntityDefinition
from app.orchestrators.outputs.flow_models import ProjectFlowState
from app.orchestrators.outputs.frontend_models import FrontendBlueprint, PageSpec
from app.orchestrators.outputs.qa_models import ApiTestPlan, ConsistencyReviewSummary, TestScenario
from app.orchestrators.outputs.requirement_models import (
    RequirementSpec,
    RequirementsStageOutput,
    TaskBreakdown,
    TaskItem,
)
from app.orchestrators.runtime import CrewAIStageRunner
from app.repositories.catalog_repository import CatalogRepository
from app.repositories.run_repository import RunRepository
from app.services.llm_config_service import LLMConfigService, RuntimeLLMConfig


StageHandler = Callable[[ProjectFlowState], Dict[str, Any]]
StageResultApplier = Callable[[ProjectFlowState, BaseModel], Dict[str, Any]]


@dataclass
class StageDefinition:
    step_code: str
    stage_name: str
    crew_name: str
    agent_code: str
    parallel_group: Optional[str]
    artifact_type: str
    artifact_title: str
    handler: StageHandler
    response_model: type[BaseModel]
    goal: str
    expected_output: str
    apply_output: StageResultApplier


@dataclass
class StageExecutionResult:
    payload: Dict[str, Any]
    runtime_mode: str
    raw_output: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class PreparedStageExecution:
    stage: StageDefinition
    resolved_agent: ResolvedAgentProfile
    prompt_snapshot: Dict[str, Any]
    task_run: TaskRun
    state_snapshot: ProjectFlowState


@dataclass(frozen=True)
class StageTemplate:
    step_code: str
    stage_name: str
    crew_name: str
    default_agent_code: str
    artifact_type: str
    artifact_title: str
    handler_name: str
    response_model: type[BaseModel]
    goal: str
    expected_output: str
    apply_output_name: str


STAGE_TEMPLATE_REGISTRY: dict[str, StageTemplate] = {
    "requirements": StageTemplate(
        step_code="requirements",
        stage_name="requirements",
        crew_name="RequirementAnalysisCrew",
        default_agent_code="product_manager",
        artifact_type="requirement_spec",
        artifact_title="需求规格说明",
        handler_name="_build_requirements",
        response_model=RequirementsStageOutput,
        goal="Analyze the raw project brief and transform it into a reusable requirement package for downstream engineering stages.",
        expected_output="Return a complete RequirementsStageOutput with both requirement_spec and task_breakdown filled in. Every list must be concrete and non-empty.",
        apply_output_name="_apply_requirements_output",
    ),
    "architecture": StageTemplate(
        step_code="architecture",
        stage_name="architecture",
        crew_name="ArchitectureDesignCrew",
        default_agent_code="software_architect",
        artifact_type="architecture_blueprint",
        artifact_title="系统架构蓝图",
        handler_name="_build_architecture",
        response_model=ArchitectureBlueprint,
        goal="Design the system architecture, deployment shape, and key ADR-level decisions for the project.",
        expected_output="Return a complete ArchitectureBlueprint with concrete modules, data flow, risks, and ADR items.",
        apply_output_name="_apply_architecture_output",
    ),
    "backend_design": StageTemplate(
        step_code="backend_design",
        stage_name="backend_design",
        crew_name="BackendDesignCrew",
        default_agent_code="backend_architect",
        artifact_type="backend_design",
        artifact_title="后端技术设计",
        handler_name="_build_backend_design",
        response_model=BackendDesign,
        goal="Produce the backend service boundaries, data model, API contracts, async strategy, and observability plan.",
        expected_output="Return a complete BackendDesign with explicit service boundaries, entities, API contracts, and implementation risks.",
        apply_output_name="_apply_backend_output",
    ),
    "frontend_design": StageTemplate(
        step_code="frontend_design",
        stage_name="frontend_design",
        crew_name="FrontendDesignCrew",
        default_agent_code="frontend_developer",
        artifact_type="frontend_blueprint",
        artifact_title="前端技术蓝图",
        handler_name="_build_frontend_design",
        response_model=FrontendBlueprint,
        goal="Translate the architecture into a usable frontend blueprint covering pages, components, state slices, and API bindings.",
        expected_output="Return a complete FrontendBlueprint with concrete page tree, component map, state slices, and real-time strategy.",
        apply_output_name="_apply_frontend_output",
    ),
    "ai_design": StageTemplate(
        step_code="ai_design",
        stage_name="ai_design",
        crew_name="AIPlatformDesignCrew",
        default_agent_code="ai_engineer",
        artifact_type="ai_integration_spec",
        artifact_title="AI 平台集成设计",
        handler_name="_build_ai_design",
        response_model=AIIntegrationSpec,
        goal="Define how AI models, prompts, output schemas, and guardrails should be integrated into the platform runtime.",
        expected_output="Return a complete AIIntegrationSpec with provider strategy, model policy, prompt policy, output schemas, evaluation plan, and guardrails.",
        apply_output_name="_apply_ai_output",
    ),
    "quality_assurance": StageTemplate(
        step_code="quality_assurance",
        stage_name="quality_assurance",
        crew_name="QualityAssuranceCrew",
        default_agent_code="api_tester",
        artifact_type="api_test_plan",
        artifact_title="测试与验收方案",
        handler_name="_build_quality_plan",
        response_model=ApiTestPlan,
        goal="Create the API and acceptance test plan that validates the project end-to-end.",
        expected_output="Return a complete ApiTestPlan with coverage focus, scenarios, acceptance criteria, and risk checklist.",
        apply_output_name="_apply_quality_output",
    ),
    "consistency_review": StageTemplate(
        step_code="consistency_review",
        stage_name="consistency_review",
        crew_name="ConsistencyReviewCrew",
        default_agent_code="software_architect",
        artifact_type="review_summary",
        artifact_title="一致性评审总结",
        handler_name="_build_review_summary",
        response_model=ConsistencyReviewSummary,
        goal="Review cross-stage consistency and identify conflicts, aligned areas, and next actions.",
        expected_output="Return a complete ConsistencyReviewSummary with an explicit coherence score, aligned areas, conflicts, and next actions.",
        apply_output_name="_apply_review_output",
    ),
}


class TechnicalDesignFlow:
    stage_template_registry = STAGE_TEMPLATE_REGISTRY
    flow_event_source = "TechnicalDesignFlow"

    def __init__(self, db: Session, flow_run: FlowRun):
        self.db = db
        self.flow_run = flow_run
        self.repository = RunRepository(db)
        self.catalog_repository = CatalogRepository(db)
        self.agent_factory = AgentFactory(db)
        workflow = self._load_workflow()
        self.runtime_config = self._load_runtime_config()
        self.crewai_runner = CrewAIStageRunner(runtime_config=self.runtime_config)
        self.state = ProjectFlowState(
            project_id=flow_run.project_id,
            flow_run_uid=flow_run.run_uid,
            workflow_code=workflow.workflow_code,
            requirement_text=flow_run.input_requirement,
            current_stage=flow_run.current_stage,
        )
        self.runtime_mode = self._resolve_runtime_mode()
        self.stages = self._build_stages(workflow)

    def _load_workflow(self) -> WorkflowTemplate:
        if not self.flow_run.workflow_template_id:
            raise ValueError("当前运行没有绑定 workflow_template_id。")

        workflow = self.catalog_repository.get_workflow_by_id(self.flow_run.workflow_template_id)
        if workflow is None:
            raise ValueError(f"未找到 id={self.flow_run.workflow_template_id} 的 workflow 配置。")
        if not workflow.enabled:
            raise ValueError(f"Workflow '{workflow.workflow_code}' 当前已停用，无法执行。")
        if not workflow.steps:
            raise ValueError(f"Workflow '{workflow.workflow_code}' 没有可执行步骤。")
        return workflow

    def _load_runtime_config(self) -> RuntimeLLMConfig | None:
        project = self.flow_run.project
        if project is None:
            raise ValueError("当前运行缺少关联项目，无法解析模型配置。")
        return LLMConfigService(self.db).get_runtime_config_for_user(project.owner_id)

    def _build_stages(self, workflow: WorkflowTemplate) -> List[StageDefinition]:
        stages: List[StageDefinition] = []
        for step in sorted(workflow.steps, key=lambda item: item.sort_order):
            template = self.stage_template_registry.get(step.step_code)
            if template is None:
                raise ValueError(
                    f"Workflow '{workflow.workflow_code}' 包含当前版本不支持的步骤 '{step.step_code}'。"
                )
            if step.step_type != "crew":
                raise ValueError(
                    f"Workflow '{workflow.workflow_code}' 的步骤 '{step.step_code}' 不是可执行的 crew 类型。"
                )

            handler = getattr(self, template.handler_name)
            apply_output = getattr(self, template.apply_output_name)
            stages.append(
                StageDefinition(
                    step_code=step.step_code,
                    stage_name=template.stage_name,
                    crew_name=template.crew_name,
                    agent_code=step.agent_code or template.default_agent_code,
                    parallel_group=step.parallel_group,
                    artifact_type=template.artifact_type,
                    artifact_title=template.artifact_title,
                    handler=handler,
                    response_model=template.response_model,
                    goal=template.goal,
                    expected_output=template.expected_output,
                    apply_output=apply_output,
                )
            )
        return stages

    def run(self) -> None:
        self._mark_run(status="RUNNING", stage="initializing")
        self._emit_event(
            "flow.started",
            self.flow_event_source,
            {"run_uid": self.flow_run.run_uid, "runtime_mode": self.runtime_mode},
        )

        for stage_batch in self._iter_stage_batches():
            self.db.refresh(self.flow_run)
            if self.flow_run.status == "CANCELLED":
                self._emit_event(
                    "flow.cancelled",
                    self.flow_event_source,
                    {
                        "current_stage": self.flow_run.current_stage,
                        "runtime_mode": self.runtime_mode,
                    },
                )
                return
            if len(stage_batch) == 1:
                self._run_stage(stage_batch[0])
                continue
            self._run_parallel_stage_group(stage_batch)

        self._mark_run(status="COMPLETED", stage="completed", finished_at=utc_now())
        self._emit_event(
            "flow.completed",
            self.flow_event_source,
            {
                "artifact_ids": self.state.artifact_ids,
                "current_stage": self.state.current_stage,
                "runtime_mode": self.runtime_mode,
            },
        )

    def _run_stage(self, stage: StageDefinition) -> None:
        prepared = self._prepare_stage_execution(stage, self.state.model_copy(deep=True))

        try:
            execution = self._execute_stage(stage, prepared.resolved_agent, prepared.state_snapshot)
            self._complete_stage_execution(prepared, execution)
        except Exception as exc:
            if self._mark_stage_execution_failed(prepared, exc, mark_run_failed=True):
                return
            raise

    def _execute_stage(
        self,
        stage: StageDefinition,
        resolved_agent: ResolvedAgentProfile,
        state: ProjectFlowState,
    ) -> StageExecutionResult:
        if self.runtime_mode == "template":
            payload = stage.handler(state)
            return StageExecutionResult(payload=payload, runtime_mode="template")

        crewai_result = self.crewai_runner.run_stage(
            crew_name=stage.crew_name,
            agent_profile=resolved_agent,
            task_description=resolved_agent.prompt_snapshot["task_description"],
            expected_output=stage.expected_output,
            output_model=stage.response_model,
        )
        structured_output = stage.response_model.model_validate(crewai_result.payload)
        payload = stage.apply_output(state, structured_output)
        return StageExecutionResult(
            payload=payload,
            runtime_mode="crewai",
            raw_output=crewai_result.raw_output,
            prompt_tokens=crewai_result.prompt_tokens,
            completion_tokens=crewai_result.completion_tokens,
        )

    def _iter_stage_batches(self) -> List[List[StageDefinition]]:
        batches: List[List[StageDefinition]] = []
        index = 0
        while index < len(self.stages):
            stage = self.stages[index]
            if stage.parallel_group:
                group = [stage]
                index += 1
                while index < len(self.stages) and self.stages[index].parallel_group == stage.parallel_group:
                    group.append(self.stages[index])
                    index += 1
                batches.append(group)
                continue
            batches.append([stage])
            index += 1
        return batches

    def _run_parallel_stage_group(self, stages: List[StageDefinition]) -> None:
        base_state = self.state.model_copy(deep=True)
        prepared_stages = [
            self._prepare_stage_execution(stage, base_state.model_copy(deep=True))
            for stage in stages
        ]
        failures: list[Exception] = []

        with ThreadPoolExecutor(max_workers=len(prepared_stages), thread_name_prefix="se-agent-stage") as executor:
            future_to_stage = {
                executor.submit(
                    self._execute_stage,
                    prepared.stage,
                    prepared.resolved_agent,
                    prepared.state_snapshot,
                ): prepared
                for prepared in prepared_stages
            }

            for future in as_completed(future_to_stage):
                prepared = future_to_stage[future]
                try:
                    execution = future.result()
                    self._complete_stage_execution(prepared, execution)
                except Exception as exc:
                    if self._mark_stage_execution_failed(prepared, exc, mark_run_failed=False):
                        continue
                    failures.append(exc)

        if failures:
            raise failures[0]

    def _prepare_stage_execution(
        self,
        stage: StageDefinition,
        state_snapshot: ProjectFlowState,
    ) -> PreparedStageExecution:
        task_description = self._build_task_description(stage, state_snapshot)
        resolved_agent = self.agent_factory.resolve(
            agent_code=stage.agent_code,
            task_description=task_description,
            context=self._build_stage_context(stage, state_snapshot),
        )
        runtime_settings = self.crewai_runner.resolve_runtime_settings(resolved_agent)
        prompt_snapshot = dict(resolved_agent.prompt_snapshot)
        prompt_snapshot["expected_output"] = stage.expected_output
        prompt_snapshot["runtime"] = {
            "mode": self.runtime_mode,
            "model": runtime_settings.model,
            "temperature": resolved_agent.temperature,
            "base_url": runtime_settings.base_url if self.runtime_mode == "crewai" else "",
            "provider_name": runtime_settings.provider_name if self.runtime_mode == "crewai" else "",
        }

        task_run = TaskRun(
            task_uid=uuid.uuid4().hex,
            flow_run_id=self.flow_run.id,
            step_code=stage.step_code,
            agent_code=stage.agent_code,
            crew_name=stage.crew_name,
            input_json={
                "state": state_snapshot.model_dump(mode="json"),
                "runtime_mode": self.runtime_mode,
            },
            status="RUNNING",
            started_at=utc_now(),
        )
        task_run = self.repository.create_task(task_run)
        task_run.prompt_snapshot = prompt_snapshot
        self.repository.save_task(task_run)

        self._mark_run(stage=stage.stage_name)
        self._emit_event(
            "task.started",
            stage.crew_name,
            {
                "step_code": stage.step_code,
                "task_uid": task_run.task_uid,
                "runtime_mode": self.runtime_mode,
            },
            task_run.id,
        )
        return PreparedStageExecution(
            stage=stage,
            resolved_agent=resolved_agent,
            prompt_snapshot=prompt_snapshot,
            task_run=task_run,
            state_snapshot=state_snapshot,
        )

    def _complete_stage_execution(
        self,
        prepared: PreparedStageExecution,
        execution: StageExecutionResult,
    ) -> None:
        next_state = self.state.model_copy(deep=True)
        payload = prepared.stage.apply_output(
            next_state,
            prepared.stage.response_model.model_validate(execution.payload),
        )
        quality_notes = self._validate_stage_payload_quality(
            prepared.stage,
            payload,
            runtime_mode=execution.runtime_mode,
        )
        markdown = self._render_markdown(
            prepared.stage,
            payload,
            runtime_mode=execution.runtime_mode,
            quality_notes=quality_notes,
        )
        self.state = next_state
        prepared.task_run.output_json = payload
        prepared.task_run.output_text = markdown
        prepared.task_run.status = "SUCCEEDED"
        prepared.task_run.finished_at = utc_now()
        prepared.task_run.token_usage_prompt = execution.prompt_tokens or len(prepared.prompt_snapshot.get("backstory", "")) // 4
        prepared.task_run.token_usage_completion = execution.completion_tokens or len(execution.raw_output or markdown) // 4
        self.repository.save_task(prepared.task_run)

        artifact = Artifact(
            artifact_uid=uuid.uuid4().hex,
            project_id=self.flow_run.project_id,
            flow_run_id=self.flow_run.id,
            artifact_type=prepared.stage.artifact_type,
            title=prepared.stage.artifact_title,
            content_markdown=markdown,
            content_json=payload,
            source_task_run_id=prepared.task_run.id,
            version_no=1,
        )
        artifact = self.repository.create_artifact(artifact)
        self.state.artifact_ids.append(artifact.id)
        self._mark_run(state_json=self.state.model_dump(mode="json"))
        self._emit_event(
            "task.completed",
            prepared.stage.crew_name,
            {
                "step_code": prepared.stage.step_code,
                "artifact_uid": artifact.artifact_uid,
                "runtime_mode": execution.runtime_mode,
            },
            prepared.task_run.id,
        )

    def _mark_stage_execution_failed(
        self,
        prepared: PreparedStageExecution,
        exc: Exception,
        *,
        mark_run_failed: bool,
    ) -> bool:
        self.db.refresh(self.flow_run)
        if self.flow_run.status == "CANCELLED":
            prepared.task_run.status = "CANCELLED"
            prepared.task_run.error_message = "Run cancelled while the current stage was still executing."
            prepared.task_run.finished_at = utc_now()
            self.repository.save_task(prepared.task_run)
            self._emit_event(
                "task.cancelled",
                prepared.stage.crew_name,
                {
                    "step_code": prepared.stage.step_code,
                    "runtime_mode": self.runtime_mode,
                },
                prepared.task_run.id,
            )
            self._emit_event(
                "flow.cancelled",
                self.flow_event_source,
                {
                    "current_stage": self.flow_run.current_stage,
                    "runtime_mode": self.runtime_mode,
                },
            )
            return True

        prepared.task_run.status = "FAILED"
        prepared.task_run.error_message = str(exc)
        prepared.task_run.finished_at = utc_now()
        self.repository.save_task(prepared.task_run)
        if mark_run_failed:
            self._mark_run(
                status="FAILED",
                stage=prepared.stage.stage_name,
                error_message=str(exc),
                finished_at=utc_now(),
            )
        self._emit_event(
            "task.failed",
            prepared.stage.crew_name,
            {
                "step_code": prepared.stage.step_code,
                "error": str(exc),
                "runtime_mode": self.runtime_mode,
            },
            prepared.task_run.id,
        )
        return False

    def _resolve_runtime_mode(self) -> str:
        if settings.agent_runtime_mode == "template":
            return "template"

        if settings.agent_runtime_mode == "crewai":
            self._ensure_ai_runtime_ready()
            return "crewai"

        if self.runtime_config or settings.has_ai_runtime_config:
            return "crewai"

        raise RuntimeError(
            "AGENT_RUNTIME_MODE=auto 且当前未检测到可用模型配置。"
            "为避免静默回退并生成 template 草稿产物，本次运行已被阻止。"
            "请先配置用户 LLM / OPENAI_API_KEY，或显式设置 AGENT_RUNTIME_MODE=template 仅作为草稿模式运行。"
        )

    def _ensure_ai_runtime_ready(self) -> None:
        if self.runtime_config or settings.has_ai_runtime_config:
            return

        raise RuntimeError(
            "AGENT_RUNTIME_MODE=crewai 但当前没有可用的模型运行配置。"
            "请在产品中配置用户自己的云端 API，或设置 OPENAI_API_KEY / OPENAI_BASE_URL。"
        )

    def _runtime_base_url(self) -> str:
        if self.runtime_config:
            return self.runtime_config.base_url
        return settings.openai_base_url

    def _build_stage_context(
        self,
        stage: StageDefinition,
        state: Optional[ProjectFlowState] = None,
    ) -> Dict[str, Any]:
        active_state = state or self.state
        context: Dict[str, Any] = {
            "workflow_code": active_state.workflow_code,
            "target_stage": stage.step_code,
            "artifact_title": stage.artifact_title,
        }

        if stage.step_code == "requirements":
            context["intake_summary"] = {
                "brief_excerpt": self._truncate_text(active_state.requirement_text, 480),
                "feature_clues": self._extract_features(active_state),
            }
            return context

        context["requirement_summary"] = self._summarize_requirement_package(active_state)

        if stage.step_code == "architecture":
            context["task_breakdown_summary"] = self._summarize_task_breakdown(active_state)
            return context

        if stage.step_code in {"backend_design", "frontend_design", "ai_design"}:
            context["task_breakdown_summary"] = self._summarize_task_breakdown(active_state)
            context["architecture_summary"] = self._summarize_architecture_blueprint(active_state)
            return context

        if stage.step_code == "quality_assurance":
            context["architecture_summary"] = self._summarize_architecture_blueprint(active_state)
            context["backend_summary"] = self._summarize_backend_design(active_state)
            context["frontend_summary"] = self._summarize_frontend_blueprint(active_state)
            context["ai_summary"] = self._summarize_ai_design(active_state)
            return context

        if stage.step_code == "consistency_review":
            context["architecture_summary"] = self._summarize_architecture_blueprint(active_state)
            context["backend_summary"] = self._summarize_backend_design(active_state)
            context["frontend_summary"] = self._summarize_frontend_blueprint(active_state)
            context["ai_summary"] = self._summarize_ai_design(active_state)
            context["qa_summary"] = self._summarize_quality_plan(active_state)
            return context

        return context

    def _build_task_description(
        self,
        stage: StageDefinition,
        state: Optional[ProjectFlowState] = None,
    ) -> str:
        active_state = state or self.state
        context_json = json.dumps(self._build_stage_context(stage, active_state), ensure_ascii=False, indent=2)
        requirement_section_title = "Original project requirement:" if stage.step_code == "requirements" else "Project brief summary:"
        requirement_section_body = self._format_requirement_brief(active_state, include_full_text=stage.step_code == "requirements")
        lines = [
            f"You are executing the '{stage.step_code}' stage of the SE-Agent Studio technical design workflow.",
            f"Artifact to produce: {stage.artifact_title}.",
            f"Stage objective: {stage.goal}",
            "",
            requirement_section_title,
            requirement_section_body,
            "",
            "Current structured context JSON:",
            context_json,
            "",
            "Answer requirements:",
            "- Return only valid structured data for the requested schema.",
            "- Use concise Chinese for human-readable fields because the project context is Chinese.",
            "- Avoid placeholders such as TBD, omitted, same as above, or generic boilerplate.",
            "- Make reasonable engineering assumptions and capture them inside the schema.",
        ]
        return "\n".join(lines).strip()

    def _mark_run(
        self,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        error_message: Optional[str] = None,
        state_json: Optional[Dict[str, Any]] = None,
        finished_at: Optional[dt.datetime] = None,
    ) -> None:
        if status is not None:
            self.flow_run.status = status
        if stage is not None:
            self.flow_run.current_stage = stage
            self.state.current_stage = stage
        if error_message is not None:
            self.flow_run.error_message = error_message
        if state_json is not None:
            self.flow_run.state_json = state_json
        else:
            self.flow_run.state_json = self.state.model_dump(mode="json")
        if status == "RUNNING" and not self.flow_run.started_at:
            self.flow_run.started_at = utc_now()
        if finished_at is not None:
            self.flow_run.finished_at = finished_at
        self.repository.save_run(self.flow_run)

    def _emit_event(
        self,
        event_type: str,
        event_source: str,
        payload: Dict[str, Any],
        task_run_id: Optional[int] = None,
    ) -> None:
        self.repository.create_event(
            RunEvent(
                flow_run_id=self.flow_run.id,
                task_run_id=task_run_id,
                event_type=event_type,
                event_source=event_source,
                payload_json=payload,
            )
        )

    def _truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "..."

    def _compact_list(self, values: Optional[List[Any]], limit: int = 5) -> List[Any]:
        if not values:
            return []
        return list(values[:limit])

    def _format_requirement_brief(self, state: ProjectFlowState, *, include_full_text: bool) -> str:
        if include_full_text or not state.requirement_spec:
            return self._truncate_text(state.requirement_text.strip(), 1200 if include_full_text else 420)
        return json.dumps(self._summarize_requirement_package(state), ensure_ascii=False, indent=2)

    def _summarize_requirement_package(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.requirement_spec:
            return {
                "brief_excerpt": self._truncate_text(state.requirement_text.strip(), 320),
                "feature_clues": self._extract_features(state),
            }

        requirement_spec = state.requirement_spec
        summary: Dict[str, Any] = {
            "project_name": requirement_spec.get("project_name", ""),
            "problem_statement": self._truncate_text(requirement_spec.get("problem_statement", state.requirement_text), 160),
            "core_features": self._compact_list(requirement_spec.get("core_features"), limit=4),
            "constraints": self._compact_list(requirement_spec.get("constraints"), limit=3),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_task_breakdown(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.task_breakdown:
            return {}

        milestones = []
        for milestone in self._compact_list(state.task_breakdown.get("milestones"), limit=4):
            if not isinstance(milestone, dict):
                continue
            milestones.append(
                {
                    "title": milestone.get("title", ""),
                    "owner_role": milestone.get("owner_role", ""),
                    "deliverable": milestone.get("deliverable", ""),
                }
            )

        summary = {
            "milestones": milestones,
            "priorities": self._compact_list(state.task_breakdown.get("priorities"), limit=3),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_architecture_blueprint(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.architecture_blueprint:
            return {}

        blueprint = state.architecture_blueprint
        adrs = []
        for item in self._compact_list(blueprint.get("adrs"), limit=3):
            if not isinstance(item, dict):
                continue
            adrs.append(
                {
                    "title": item.get("title", ""),
                    "decision": self._truncate_text(item.get("decision", ""), 80),
                }
            )

        summary = {
            "architecture_style": blueprint.get("architecture_style", ""),
            "core_modules": self._compact_list(blueprint.get("core_modules"), limit=5),
            "deployment_units": self._compact_list(blueprint.get("deployment_units"), limit=4),
            "key_decisions": self._compact_list(blueprint.get("key_decisions"), limit=3),
            "adrs": adrs[:2],
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_backend_design(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.backend_design:
            return {}

        design = state.backend_design
        entities = []
        for entity in self._compact_list(design.get("entities"), limit=4):
            if not isinstance(entity, dict):
                continue
            entities.append(
                {
                    "name": entity.get("name", ""),
                    "purpose": self._truncate_text(entity.get("purpose", ""), 80),
                }
            )

        api_contracts = []
        for contract in self._compact_list(design.get("api_contracts"), limit=5):
            if not isinstance(contract, dict):
                continue
            api_contracts.append(f"{contract.get('method', '')} {contract.get('path', '')}".strip())

        summary = {
            "service_boundary": self._compact_list(design.get("service_boundary"), limit=4),
            "entities": entities,
            "api_contracts": api_contracts,
            "async_strategy": self._compact_list(design.get("async_strategy"), limit=3),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_frontend_blueprint(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.frontend_blueprint:
            return {}

        blueprint = state.frontend_blueprint
        page_tree = []
        for page in self._compact_list(blueprint.get("page_tree"), limit=4):
            if not isinstance(page, dict):
                continue
            page_tree.append(page.get("page_name", ""))

        summary = {
            "page_tree": page_tree,
            "component_map": self._compact_list(blueprint.get("component_map"), limit=5),
            "api_bindings": self._compact_list(blueprint.get("api_bindings"), limit=4),
            "realtime_strategy": self._compact_list(blueprint.get("realtime_strategy"), limit=3),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_ai_design(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.ai_integration_spec:
            return {}

        spec = state.ai_integration_spec
        summary = {
            "provider_strategy": self._compact_list(spec.get("provider_strategy"), limit=3),
            "output_schemas": self._compact_list(spec.get("output_schemas"), limit=4),
            "guardrails": self._compact_list(spec.get("guardrails"), limit=4),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_quality_plan(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.api_test_plan:
            return {}

        plan = state.api_test_plan
        scenarios = []
        for scenario in self._compact_list(plan.get("core_scenarios"), limit=4):
            if not isinstance(scenario, dict):
                continue
            scenarios.append(scenario.get("title", ""))

        summary = {
            "coverage_focus": self._compact_list(plan.get("coverage_focus"), limit=4),
            "core_scenarios": scenarios,
            "acceptance_criteria": self._compact_list(plan.get("acceptance_criteria"), limit=3),
        }
        return {key: value for key, value in summary.items() if value}

    def _extract_features(self, state: Optional[ProjectFlowState] = None) -> List[str]:
        active_state = state or self.state
        base_text = active_state.requirement_text.replace("。", "\n").replace("；", "\n").replace(";", "\n")
        features = [item.strip(" -\t") for item in base_text.splitlines() if item.strip()]
        unique: List[str] = []
        for item in features:
            if item not in unique:
                unique.append(item)
        return unique[:6] or ["定义项目需求输入", "生成结构化工程产物", "展示运行状态与产物"]

    def _apply_requirements_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = RequirementsStageOutput.model_validate(output)
        validate_requirement_spec(structured_output.requirement_spec)
        state.requirement_spec = structured_output.requirement_spec.model_dump(mode="json")
        state.task_breakdown = structured_output.task_breakdown.model_dump(mode="json")
        return {
            "requirement_spec": state.requirement_spec,
            "task_breakdown": state.task_breakdown,
        }

    def _apply_architecture_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = ArchitectureBlueprint.model_validate(output)
        validate_architecture_blueprint(structured_output)
        state.architecture_blueprint = structured_output.model_dump(mode="json")
        return state.architecture_blueprint

    def _apply_backend_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = BackendDesign.model_validate(output)
        state.backend_design = structured_output.model_dump(mode="json")
        return state.backend_design

    def _apply_frontend_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = FrontendBlueprint.model_validate(output)
        state.frontend_blueprint = structured_output.model_dump(mode="json")
        return state.frontend_blueprint

    def _apply_ai_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = AIIntegrationSpec.model_validate(output)
        state.ai_integration_spec = structured_output.model_dump(mode="json")
        return state.ai_integration_spec

    def _apply_quality_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = ApiTestPlan.model_validate(output)
        state.api_test_plan = structured_output.model_dump(mode="json")
        return state.api_test_plan

    def _apply_review_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = ConsistencyReviewSummary.model_validate(output)
        state.review_summary = structured_output.model_dump(mode="json")
        return state.review_summary

    def _build_requirements(self, state: ProjectFlowState) -> Dict[str, Any]:
        features = list(
            dict.fromkeys(
                [
                    *self._extract_features(state),
                    "将项目需求整理为结构化规格",
                    "支持创建运行并持续追踪阶段状态",
                    "支持统一查看和管理阶段产物",
                ]
            )
        )[:6]
        spec = RequirementSpec(
            project_name=features[0][:32] if features else "SE-Agent Studio Project",
            problem_statement=state.requirement_text[:240],
            target_users=["课程设计学生", "项目指导教师", "系统管理员"],
            core_features=features,
            non_functional_requirements=["运行过程可追踪", "阶段输出必须结构化", "支持异步运行与状态刷新"],
            constraints=["首版采用固定流程模板", "后端使用 FastAPI + SQLAlchemy", "前端使用 Vue 3 + Pinia"],
            assumptions=["当前以单租户课程项目场景为主", "管理员负责维护 Agent 和 Workflow 模板"],
            open_questions=["是否接入真实 OpenAI 兼容模型", "是否在第一阶段启用人工审核节点"],
        )
        validate_requirement_spec(spec)
        task_breakdown = TaskBreakdown(
            milestones=[
                TaskItem(title="需求结构化", owner_role="Product Manager", objective="固化项目范围与约束", deliverable="RequirementSpec"),
                TaskItem(title="系统架构设计", owner_role="Software Architect", objective="定义模块边界与关键决策", deliverable="ArchitectureBlueprint"),
                TaskItem(title="前后端方案设计", owner_role="Backend/Frontend", objective="形成可开发的实现蓝图", deliverable="BackendDesign / FrontendBlueprint"),
            ],
            priorities=["先打通固定工作流", "保证结构化输出", "补齐监控和产物中心"],
            clarification_list=["明确部署环境", "明确模型提供方", "明确是否需要用户体系"],
        )
        state.requirement_spec = spec.model_dump(mode="json")
        state.task_breakdown = task_breakdown.model_dump(mode="json")
        return {
            "requirement_spec": state.requirement_spec,
            "task_breakdown": state.task_breakdown,
        }

    def _build_architecture(self, state: ProjectFlowState) -> Dict[str, Any]:
        blueprint = ArchitectureBlueprint(
            architecture_style="模块化单体 + 异步 Worker + 固定 Flow 编排",
            core_modules=[
                "FastAPI API 层",
                "应用服务层",
                "Flow / Crew 编排层",
                "Worker 执行层",
                "项目 / 运行 / 产物数据层",
                "Vue 前端工作台",
            ],
            data_flow=[
                "用户提交需求 -> 创建 flow_run -> 投递执行任务",
                "Worker 分阶段生成结构化产物 -> task_run / artifact 落库",
                "前端通过 SSE / 轮询读取状态与事件",
            ],
            deployment_units=["web-api", "worker", "mysql", "redis", "frontend"],
            key_decisions=[
                "Flow 负责总控，Crew 负责阶段任务",
                "Schema First，所有关键产物结构化",
                "首版采用固定模板流程以换取稳定性",
            ],
            risks=["真实 LLM 接入后成本与稳定性需评估", "SSE 与 Celery 一致性需要联调", "管理员配置能力仍需继续完善"],
            adrs=[
                ADRItem(title="ADR-001 采用模块化单体", decision="优先单体架构", rationale="更适合课程项目迭代速度", trade_off="横向扩展能力弱于微服务"),
                ADRItem(title="ADR-002 Flow First", decision="用显式 Flow 管理阶段", rationale="便于追踪、重试和展示", trade_off="开发复杂度略高于大 Crew 直跑"),
            ],
        )
        validate_architecture_blueprint(blueprint)
        state.architecture_blueprint = blueprint.model_dump(mode="json")
        return state.architecture_blueprint

    def _build_backend_design(self, state: ProjectFlowState) -> Dict[str, Any]:
        design = BackendDesign(
            service_boundary=["项目管理服务", "运行编排服务", "产物中心服务", "管理配置服务"],
            entities=[
                EntityDefinition(name="project", purpose="承载课程项目上下文", key_fields=["uid", "name", "summary", "requirement_text"]),
                EntityDefinition(name="flow_run", purpose="记录一次完整协作运行", key_fields=["run_uid", "status", "current_stage", "state_json"]),
                EntityDefinition(name="artifact", purpose="沉淀阶段产物", key_fields=["artifact_uid", "artifact_type", "content_json", "content_markdown"]),
            ],
            api_contracts=[
                ApiEndpointContract(method="POST", path="/api/v1/projects/{project_uid}/runs", summary="创建运行", request_shape="RunCreate", response_shape="FlowRunDetail"),
                ApiEndpointContract(method="GET", path="/api/v1/runs/{run_uid}/stream", summary="订阅运行状态", request_shape="None", response_shape="SSE stream"),
                ApiEndpointContract(method="GET", path="/api/v1/projects/{project_uid}/artifacts", summary="读取项目产物", request_shape="None", response_shape="ArtifactListItem[]"),
            ],
            async_strategy=["本地开发支持 background thread", "生产模式切换为 Celery + Redis", "Flow 状态按阶段持久化到数据库"],
            observability=["run_event 事件流", "阶段耗时", "任务状态与错误信息", "token 粗略使用量"],
            risks=["SQLite 仅适合开发", "恢复执行语义还需进一步增强", "真正的权限隔离尚未实现"],
        )
        state.backend_design = design.model_dump(mode="json")
        return state.backend_design

    def _build_frontend_design(self, state: ProjectFlowState) -> Dict[str, Any]:
        blueprint = FrontendBlueprint(
            page_tree=[
                PageSpec(page_name="项目列表", goal="查看并创建项目", key_sections=["项目卡片", "运行入口", "最近活动"]),
                PageSpec(page_name="项目详情", goal="编辑需求并查看运行概览", key_sections=["项目信息", "最近运行", "产物摘要"]),
                PageSpec(page_name="运行监控", goal="追踪当前阶段与事件", key_sections=["阶段轨道", "事件时间线", "任务详情"]),
                PageSpec(page_name="产物中心", goal="统一阅读产物", key_sections=["类型分组", "Markdown 预览", "导出入口"]),
            ],
            component_map=["ShellLayout", "ProjectHero", "RunStageRail", "EventTimeline", "ArtifactPanel", "AdminTables"],
            state_slices=["authStore", "projectStore", "runStore", "artifactStore", "adminConfigStore"],
            api_bindings=[
                "GET /api/v1/projects",
                "POST /api/v1/projects/{project_uid}/runs",
                "GET /api/v1/runs/{run_uid}",
                "GET /api/v1/runs/{run_uid}/events",
            ],
            realtime_strategy=["优先使用 SSE", "降级为轮询", "在运行详情页高亮当前阶段"],
        )
        state.frontend_blueprint = blueprint.model_dump(mode="json")
        return state.frontend_blueprint

    def _build_ai_design(self, state: ProjectFlowState) -> Dict[str, Any]:
        spec = AIIntegrationSpec(
            provider_strategy=["封装 OpenAI 兼容接口", "保留 DeepSeek / Qwen / 本地模型扩展口", "按 agent_profile 控制默认模型"],
            model_policy=["首版先做单模型默认配置", "AgentFactory 负责注入模型参数", "运行时保存 prompt snapshot"],
            prompt_policy=["角色 Prompt 来源于 agents/*.md", "运行前固化 prompt 版本快照", "Guardrail 失败时允许一次修复重试"],
            output_schemas=["RequirementSpec", "ArchitectureBlueprint", "BackendDesign", "FrontendBlueprint", "ApiTestPlan"],
            evaluation_plan=["检查字段完整性", "检查跨阶段一致性", "跟踪失败率和 token 粗用量"],
            guardrails=["字段必填校验", "列表不得为空", "禁止占位式输出", "关键接口命名一致性校验"],
        )
        state.ai_integration_spec = spec.model_dump(mode="json")
        return state.ai_integration_spec

    def _build_quality_plan(self, state: ProjectFlowState) -> Dict[str, Any]:
        plan = ApiTestPlan(
            coverage_focus=["项目管理接口", "运行创建与状态追踪", "SSE 事件流", "产物查询与导出"],
            core_scenarios=[
                TestScenario(title="创建项目并启动运行", category="happy_path", expected_result="返回 run_uid 且状态进入 QUEUED/RUNNING"),
                TestScenario(title="运行失败时写入错误事件", category="failure", expected_result="flow_run.status=FAILED 且 run_event 持久化"),
                TestScenario(title="产物中心按类型展示", category="artifact", expected_result="返回分组后的 artifact 列表"),
            ],
            acceptance_criteria=[
                "创建运行接口在 3 秒内返回 run_uid",
                "每个阶段至少落一条 task_run 和一份 artifact",
                "运行监控页能看到当前阶段和事件时间线",
            ],
            risk_checklist=["取消 / 恢复语义需进一步验证", "真实模型超时重试策略待补", "权限隔离和审计待补"],
        )
        state.api_test_plan = plan.model_dump(mode="json")
        return state.api_test_plan

    def _build_review_summary(self, state: ProjectFlowState) -> Dict[str, Any]:
        summary = ConsistencyReviewSummary(
            coherence_score=88,
            aligned_areas=["阶段产物命名一致", "后端 API 与前端页面链路基本对应", "运行追踪数据模型已贯通"],
            conflicts=["真实 CrewAI 调度尚未接入", "简化了权限与导出能力", "恢复执行仍是从头重跑"],
            next_actions=["接入真实 CrewAI Crew/Flow", "补 Alembic migration", "接通 MySQL + Redis + Celery 集成验证"],
        )
        state.review_summary = summary.model_dump(mode="json")
        return state.review_summary

    def _validate_stage_payload_quality(
        self,
        stage: StageDefinition,
        payload: Dict[str, Any],
        *,
        runtime_mode: str,
    ) -> List[str]:
        text_fragments = self._collect_text_fragments(payload)
        if not text_fragments:
            raise ValueError(f"阶段 {stage.step_code} 未生成可读内容，质量门禁拒绝落库。")

        substring_placeholder_markers = (
            "tbd",
            "todo",
            "placeholder",
            "same as above",
            "lorem ipsum",
            "待补充",
            "暂无",
            "n/a",
        )
        exact_placeholder_markers = {"同上", "略"}
        lowered_fragments = [item.lower() for item in text_fragments]
        normalized_fragments = {item.strip().lower() for item in text_fragments if item.strip()}
        matched_markers = sorted(
            {
                marker
                for marker in substring_placeholder_markers
                if any(marker in fragment for fragment in lowered_fragments)
            }
            | {
                marker
                for marker in exact_placeholder_markers
                if marker in normalized_fragments
            }
        )
        if matched_markers:
            raise ValueError(
                f"阶段 {stage.step_code} 未通过质量门禁：检测到占位式表述 {', '.join(matched_markers)}。"
            )

        combined_length = sum(len(item) for item in text_fragments)
        min_text_length = {
            "requirements": 120,
            "architecture": 120,
            "backend_design": 100,
            "frontend_design": 100,
            "ai_design": 80,
            "quality_assurance": 80,
            "consistency_review": 60,
        }.get(stage.step_code, 80)
        if combined_length < min_text_length:
            raise ValueError(
                f"阶段 {stage.step_code} 未通过质量门禁：文本信息量不足，当前仅 {combined_length} 个字符。"
            )

        list_requirements = {
            "requirements": {
                "requirement_spec.target_users": 1,
                "requirement_spec.core_features": 2,
                "task_breakdown.milestones": 2,
                "task_breakdown.priorities": 2,
            },
            "architecture": {
                "core_modules": 3,
                "data_flow": 2,
                "key_decisions": 2,
                "adrs": 1,
            },
            "backend_design": {
                "service_boundary": 2,
                "entities": 2,
                "api_contracts": 2,
                "observability": 2,
            },
            "frontend_design": {
                "page_tree": 2,
                "component_map": 3,
                "api_bindings": 2,
            },
            "ai_design": {
                "provider_strategy": 2,
                "prompt_policy": 2,
                "guardrails": 2,
            },
            "quality_assurance": {
                "coverage_focus": 2,
                "core_scenarios": 2,
                "acceptance_criteria": 2,
            },
            "consistency_review": {
                "aligned_areas": 1,
                "conflicts": 1,
                "next_actions": 1,
            },
        }.get(stage.step_code, {})
        for path, minimum in list_requirements.items():
            self._assert_min_items(payload, path, minimum, stage.step_code)

        notes = [
            f"已通过基础质量门禁：识别到 {len(text_fragments)} 段文本，累计 {combined_length} 个字符。",
            f"当前运行模式：{runtime_mode}。",
        ]
        if runtime_mode == "template":
            notes.append("当前产物属于显式 template 草稿，仅适合流程预演和结构校对。")
        return notes

    def _collect_text_fragments(self, value: Any) -> List[str]:
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if isinstance(value, dict):
            fragments: List[str] = []
            for item in value.values():
                fragments.extend(self._collect_text_fragments(item))
            return fragments
        if isinstance(value, list):
            fragments: List[str] = []
            for item in value:
                fragments.extend(self._collect_text_fragments(item))
            return fragments
        return []

    def _read_nested_value(self, payload: Dict[str, Any], path: str) -> Any:
        current: Any = payload
        for segment in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
        return current

    def _assert_min_items(self, payload: Dict[str, Any], path: str, minimum: int, stage_code: str) -> None:
        current = self._read_nested_value(payload, path)
        count = len(current) if isinstance(current, list) else 0
        if count < minimum:
            raise ValueError(
                f"阶段 {stage_code} 未通过质量门禁：字段 '{path}' 至少需要 {minimum} 项，当前为 {count} 项。"
            )

    def _render_markdown(
        self,
        stage: StageDefinition,
        payload: Dict[str, Any],
        *,
        runtime_mode: str,
        quality_notes: List[str],
    ) -> str:
        renderer = getattr(self, f"_render_{stage.step_code}_markdown", None)
        body_lines = renderer(payload) if callable(renderer) else self._render_generic_markdown(payload)

        lines = [
            f"# {stage.artifact_title}",
            "",
            "## 文档元信息",
            "",
            "| 字段 | 内容 |",
            "| --- | --- |",
            f"| 阶段 | `{stage.step_code}` |",
            f"| 运行模式 | `{runtime_mode}` |",
            "",
        ]
        if runtime_mode == "template":
            lines.extend(
                [
                    "> ⚠️ 当前文档由显式 template 草稿模式生成，仅供流程演示与结构预览，不能作为正式设计结论。",
                    "",
                ]
            )
        lines.extend(["## 质量检查", ""])
        lines.extend(self._render_bullet_list(quality_notes))
        lines.extend(["", *body_lines])
        return "\n".join(lines).strip()

    def _render_requirements_markdown(self, payload: Dict[str, Any]) -> List[str]:
        spec = payload.get("requirement_spec") or {}
        breakdown = payload.get("task_breakdown") or {}
        milestone_rows = []
        for item in breakdown.get("milestones", []):
            if not isinstance(item, dict):
                continue
            milestone_rows.append(
                [
                    item.get("title", ""),
                    item.get("owner_role", ""),
                    item.get("objective", ""),
                    item.get("deliverable", ""),
                ]
            )

        lines = [
            "## 项目概述",
            "",
            f"**项目名称**：{spec.get('project_name', '未命名项目')}",
            "",
            f"**问题陈述**：{spec.get('problem_statement', '')}",
            "",
            "## 目标用户",
            "",
            *self._render_bullet_list(spec.get("target_users", [])),
            "",
            "## 核心功能",
            "",
            *self._render_bullet_list(spec.get("core_features", [])),
            "",
            "## 非功能要求",
            "",
            *self._render_bullet_list(spec.get("non_functional_requirements", [])),
            "",
            "## 约束条件",
            "",
            *self._render_bullet_list(spec.get("constraints", [])),
            "",
            "## 假设前提",
            "",
            *self._render_bullet_list(spec.get("assumptions", [])),
            "",
            "## 待确认问题",
            "",
            *self._render_bullet_list(spec.get("open_questions", [])),
            "",
            "## 任务拆解",
            "",
            *self._render_markdown_table(
                ["里程碑", "负责角色", "目标", "交付物"],
                milestone_rows,
            ),
            "",
            "## 实施优先级",
            "",
            *self._render_bullet_list(breakdown.get("priorities", [])),
            "",
            "## 澄清清单",
            "",
            *self._render_bullet_list(breakdown.get("clarification_list", [])),
        ]
        return lines

    def _render_architecture_markdown(self, payload: Dict[str, Any]) -> List[str]:
        adr_rows = []
        for item in payload.get("adrs", []):
            if not isinstance(item, dict):
                continue
            adr_rows.append(
                [
                    item.get("title", ""),
                    item.get("decision", ""),
                    item.get("rationale", ""),
                    item.get("trade_off", ""),
                ]
            )

        return [
            "## 架构概览",
            "",
            f"**架构风格**：{payload.get('architecture_style', '')}",
            "",
            "## 核心模块",
            "",
            *self._render_bullet_list(payload.get("core_modules", [])),
            "",
            "## 关键数据流",
            "",
            *self._render_numbered_list(payload.get("data_flow", [])),
            "",
            "## 部署单元",
            "",
            *self._render_bullet_list(payload.get("deployment_units", [])),
            "",
            "## 关键决策",
            "",
            *self._render_bullet_list(payload.get("key_decisions", [])),
            "",
            "## ADR 记录",
            "",
            *self._render_markdown_table(
                ["标题", "决策", "原因", "代价 / 权衡"],
                adr_rows,
            ),
            "",
            "## 主要风险",
            "",
            *self._render_bullet_list(payload.get("risks", [])),
        ]

    def _render_backend_design_markdown(self, payload: Dict[str, Any]) -> List[str]:
        api_rows = []
        for item in payload.get("api_contracts", []):
            if not isinstance(item, dict):
                continue
            api_rows.append(
                [
                    item.get("method", ""),
                    item.get("path", ""),
                    item.get("summary", ""),
                    item.get("request_shape", ""),
                    item.get("response_shape", ""),
                ]
            )

        lines = [
            "## 服务边界",
            "",
            *self._render_bullet_list(payload.get("service_boundary", [])),
            "",
            "## 领域实体",
            "",
        ]
        for entity in payload.get("entities", []):
            if not isinstance(entity, dict):
                continue
            lines.extend(
                [
                    f"### 实体：`{entity.get('name', 'unknown')}`",
                    "",
                    f"- **用途**：{entity.get('purpose', '')}",
                    f"- **关键字段**：{self._format_inline_list(entity.get('key_fields', []))}",
                    "",
                ]
            )

        lines.extend(
            [
                "## API 契约",
                "",
                *self._render_markdown_table(
                    ["方法", "路径", "说明", "请求", "响应"],
                    api_rows,
                ),
                "",
                "## 异步策略",
                "",
                *self._render_bullet_list(payload.get("async_strategy", [])),
                "",
                "## 可观测性",
                "",
                *self._render_bullet_list(payload.get("observability", [])),
                "",
                "## 主要风险",
                "",
                *self._render_bullet_list(payload.get("risks", [])),
            ]
        )
        return lines

    def _render_frontend_design_markdown(self, payload: Dict[str, Any]) -> List[str]:
        lines = [
            "## 页面结构",
            "",
        ]
        for page in payload.get("page_tree", []):
            if not isinstance(page, dict):
                continue
            lines.extend(
                [
                    f"### 页面：{page.get('page_name', '未命名页面')}",
                    "",
                    f"- **目标**：{page.get('goal', '')}",
                    f"- **关键区域**：{self._format_inline_list(page.get('key_sections', []))}",
                    "",
                ]
            )

        lines.extend(
            [
                "## 组件边界",
                "",
                *self._render_bullet_list(payload.get("component_map", [])),
                "",
                "## 状态管理",
                "",
                *self._render_bullet_list(payload.get("state_slices", [])),
                "",
                "## API 绑定",
                "",
                *self._render_bullet_list(payload.get("api_bindings", [])),
                "",
                "## 实时更新策略",
                "",
                *self._render_bullet_list(payload.get("realtime_strategy", [])),
            ]
        )
        return lines

    def _render_ai_design_markdown(self, payload: Dict[str, Any]) -> List[str]:
        return [
            "## Provider 策略",
            "",
            *self._render_bullet_list(payload.get("provider_strategy", [])),
            "",
            "## 模型策略",
            "",
            *self._render_bullet_list(payload.get("model_policy", [])),
            "",
            "## Prompt 策略",
            "",
            *self._render_bullet_list(payload.get("prompt_policy", [])),
            "",
            "## 输出 Schema",
            "",
            *self._render_bullet_list(payload.get("output_schemas", [])),
            "",
            "## 评估计划",
            "",
            *self._render_bullet_list(payload.get("evaluation_plan", [])),
            "",
            "## Guardrails",
            "",
            *self._render_bullet_list(payload.get("guardrails", [])),
        ]

    def _render_quality_assurance_markdown(self, payload: Dict[str, Any]) -> List[str]:
        scenario_rows = []
        for item in payload.get("core_scenarios", []):
            if not isinstance(item, dict):
                continue
            scenario_rows.append(
                [
                    item.get("title", ""),
                    item.get("category", ""),
                    item.get("expected_result", ""),
                ]
            )

        return [
            "## 覆盖重点",
            "",
            *self._render_bullet_list(payload.get("coverage_focus", [])),
            "",
            "## 核心测试场景",
            "",
            *self._render_markdown_table(["场景", "类别", "期望结果"], scenario_rows),
            "",
            "## 验收标准",
            "",
            *self._render_bullet_list(payload.get("acceptance_criteria", [])),
            "",
            "## 风险清单",
            "",
            *self._render_bullet_list(payload.get("risk_checklist", [])),
        ]

    def _render_consistency_review_markdown(self, payload: Dict[str, Any]) -> List[str]:
        return [
            "## 总体结论",
            "",
            f"**一致性评分**：{payload.get('coherence_score', 0)} / 100",
            "",
            "## 已对齐内容",
            "",
            *self._render_bullet_list(payload.get("aligned_areas", [])),
            "",
            "## 当前冲突",
            "",
            *self._render_bullet_list(payload.get("conflicts", [])),
            "",
            "## 后续动作",
            "",
            *self._render_bullet_list(payload.get("next_actions", [])),
        ]

    def _render_generic_markdown(self, payload: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        for key, value in payload.items():
            if key.startswith("_"):
                continue
            lines.extend([f"## {key}", ""])
            if isinstance(value, list):
                lines.extend(self._render_bullet_list(value))
            elif isinstance(value, dict):
                lines.extend(self._render_bullet_list([json.dumps(value, ensure_ascii=False)]))
            else:
                lines.append(str(value))
            lines.append("")
        return lines

    def _render_bullet_list(self, values: List[Any]) -> List[str]:
        cleaned_values = [self._normalize_inline_text(value) for value in values if self._normalize_inline_text(value)]
        if not cleaned_values:
            return ["- 暂无"]
        return [f"- {item}" for item in cleaned_values]

    def _render_numbered_list(self, values: List[Any]) -> List[str]:
        cleaned_values = [self._normalize_inline_text(value) for value in values if self._normalize_inline_text(value)]
        if not cleaned_values:
            return ["1. 暂无"]
        return [f"{index}. {item}" for index, item in enumerate(cleaned_values, start=1)]

    def _render_markdown_table(self, headers: List[str], rows: List[List[Any]]) -> List[str]:
        normalized_rows = rows or [["暂无" for _ in headers]]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in normalized_rows:
            padded_row = list(row)[: len(headers)]
            if len(padded_row) < len(headers):
                padded_row.extend([""] * (len(headers) - len(padded_row)))
            lines.append(
                "| " + " | ".join(self._escape_markdown_cell(item) for item in padded_row) + " |"
            )
        return lines

    def _format_inline_list(self, values: List[Any]) -> str:
        cleaned_values = [self._normalize_inline_text(value) for value in values if self._normalize_inline_text(value)]
        if not cleaned_values:
            return "暂无"
        return "、".join(f"`{item}`" for item in cleaned_values)

    def _normalize_inline_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        return str(value).replace("\n", " ").strip()

    def _escape_markdown_cell(self, value: Any) -> str:
        return self._normalize_inline_text(value).replace("|", "\\|")
