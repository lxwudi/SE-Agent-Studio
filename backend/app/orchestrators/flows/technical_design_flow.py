import datetime as dt
import json
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.clock import utc_now
from app.core.config import settings
from app.db.models import Artifact, FlowRun, RunEvent, TaskRun
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
from app.repositories.run_repository import RunRepository


StageHandler = Callable[[ProjectFlowState], Dict[str, Any]]
StageResultApplier = Callable[[ProjectFlowState, BaseModel], Dict[str, Any]]


@dataclass
class StageDefinition:
    step_code: str
    stage_name: str
    crew_name: str
    agent_code: str
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


class TechnicalDesignFlow:
    def __init__(self, db: Session, flow_run: FlowRun):
        self.db = db
        self.flow_run = flow_run
        self.repository = RunRepository(db)
        self.agent_factory = AgentFactory(db)
        self.crewai_runner = CrewAIStageRunner()
        self.state = ProjectFlowState(
            project_id=flow_run.project_id,
            flow_run_uid=flow_run.run_uid,
            workflow_code="technical_design_v1",
            requirement_text=flow_run.input_requirement,
            current_stage=flow_run.current_stage,
        )
        self.runtime_mode = self._resolve_runtime_mode()
        self.stages: List[StageDefinition] = [
            StageDefinition(
                step_code="requirements",
                stage_name="requirements",
                crew_name="RequirementAnalysisCrew",
                agent_code="product_manager",
                artifact_type="requirement_spec",
                artifact_title="需求规格说明",
                handler=self._build_requirements,
                response_model=RequirementsStageOutput,
                goal="Analyze the raw project brief and transform it into a reusable requirement package for downstream engineering stages.",
                expected_output="Return a complete RequirementsStageOutput with both requirement_spec and task_breakdown filled in. Every list must be concrete and non-empty.",
                apply_output=self._apply_requirements_output,
            ),
            StageDefinition(
                step_code="architecture",
                stage_name="architecture",
                crew_name="ArchitectureDesignCrew",
                agent_code="software_architect",
                artifact_type="architecture_blueprint",
                artifact_title="系统架构蓝图",
                handler=self._build_architecture,
                response_model=ArchitectureBlueprint,
                goal="Design the system architecture, deployment shape, and key ADR-level decisions for the project.",
                expected_output="Return a complete ArchitectureBlueprint with concrete modules, data flow, risks, and ADR items.",
                apply_output=self._apply_architecture_output,
            ),
            StageDefinition(
                step_code="backend_design",
                stage_name="backend_design",
                crew_name="BackendDesignCrew",
                agent_code="backend_architect",
                artifact_type="backend_design",
                artifact_title="后端技术设计",
                handler=self._build_backend_design,
                response_model=BackendDesign,
                goal="Produce the backend service boundaries, data model, API contracts, async strategy, and observability plan.",
                expected_output="Return a complete BackendDesign with explicit service boundaries, entities, API contracts, and implementation risks.",
                apply_output=self._apply_backend_output,
            ),
            StageDefinition(
                step_code="frontend_design",
                stage_name="frontend_design",
                crew_name="FrontendDesignCrew",
                agent_code="frontend_developer",
                artifact_type="frontend_blueprint",
                artifact_title="前端技术蓝图",
                handler=self._build_frontend_design,
                response_model=FrontendBlueprint,
                goal="Translate the architecture into a usable frontend blueprint covering pages, components, state slices, and API bindings.",
                expected_output="Return a complete FrontendBlueprint with concrete page tree, component map, state slices, and real-time strategy.",
                apply_output=self._apply_frontend_output,
            ),
            StageDefinition(
                step_code="ai_design",
                stage_name="ai_design",
                crew_name="AIPlatformDesignCrew",
                agent_code="ai_engineer",
                artifact_type="ai_integration_spec",
                artifact_title="AI 平台集成设计",
                handler=self._build_ai_design,
                response_model=AIIntegrationSpec,
                goal="Define how AI models, prompts, output schemas, and guardrails should be integrated into the platform runtime.",
                expected_output="Return a complete AIIntegrationSpec with provider strategy, model policy, prompt policy, output schemas, evaluation plan, and guardrails.",
                apply_output=self._apply_ai_output,
            ),
            StageDefinition(
                step_code="quality_assurance",
                stage_name="quality_assurance",
                crew_name="QualityAssuranceCrew",
                agent_code="api_tester",
                artifact_type="api_test_plan",
                artifact_title="测试与验收方案",
                handler=self._build_quality_plan,
                response_model=ApiTestPlan,
                goal="Create the API and acceptance test plan that validates the project end-to-end.",
                expected_output="Return a complete ApiTestPlan with coverage focus, scenarios, acceptance criteria, and risk checklist.",
                apply_output=self._apply_quality_output,
            ),
            StageDefinition(
                step_code="consistency_review",
                stage_name="consistency_review",
                crew_name="ConsistencyReviewCrew",
                agent_code="software_architect",
                artifact_type="review_summary",
                artifact_title="一致性评审总结",
                handler=self._build_review_summary,
                response_model=ConsistencyReviewSummary,
                goal="Review cross-stage consistency and identify conflicts, aligned areas, and next actions.",
                expected_output="Return a complete ConsistencyReviewSummary with an explicit coherence score, aligned areas, conflicts, and next actions.",
                apply_output=self._apply_review_output,
            ),
        ]

    def run(self) -> None:
        self._mark_run(status="RUNNING", stage="initializing")
        self._emit_event(
            "flow.started",
            "TechnicalDesignFlow",
            {"run_uid": self.flow_run.run_uid, "runtime_mode": self.runtime_mode},
        )

        for stage in self.stages:
            self.db.refresh(self.flow_run)
            if self.flow_run.status == "CANCELLED":
                self._emit_event(
                    "flow.cancelled",
                    "TechnicalDesignFlow",
                    {
                        "current_stage": self.flow_run.current_stage,
                        "runtime_mode": self.runtime_mode,
                    },
                )
                return
            self._run_stage(stage)

        self._mark_run(status="COMPLETED", stage="completed", finished_at=utc_now())
        self._emit_event(
            "flow.completed",
            "TechnicalDesignFlow",
            {
                "artifact_ids": self.state.artifact_ids,
                "current_stage": self.state.current_stage,
                "runtime_mode": self.runtime_mode,
            },
        )

    def _run_stage(self, stage: StageDefinition) -> None:
        task_description = self._build_task_description(stage)
        resolved_agent = self.agent_factory.resolve(
            agent_code=stage.agent_code,
            task_description=task_description,
            context=self._build_stage_context(stage),
        )
        prompt_snapshot = dict(resolved_agent.prompt_snapshot)
        prompt_snapshot["expected_output"] = stage.expected_output
        prompt_snapshot["runtime"] = {
            "mode": self.runtime_mode,
            "model": resolved_agent.model or settings.default_model,
            "temperature": resolved_agent.temperature,
            "base_url": settings.openai_base_url if self.runtime_mode == "crewai" else "",
        }

        task_run = TaskRun(
            task_uid=uuid.uuid4().hex,
            flow_run_id=self.flow_run.id,
            step_code=stage.step_code,
            agent_code=stage.agent_code,
            crew_name=stage.crew_name,
            input_json={
                "state": self.state.model_dump(mode="json"),
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

        try:
            execution = self._execute_stage(stage, resolved_agent)
            markdown = self._render_markdown(stage.artifact_title, execution.payload)
            task_run.output_json = execution.payload
            task_run.output_text = markdown
            task_run.status = "SUCCEEDED"
            task_run.finished_at = utc_now()
            task_run.token_usage_prompt = execution.prompt_tokens or len(prompt_snapshot.get("backstory", "")) // 4
            task_run.token_usage_completion = execution.completion_tokens or len(execution.raw_output or markdown) // 4
            self.repository.save_task(task_run)

            artifact = Artifact(
                artifact_uid=uuid.uuid4().hex,
                project_id=self.flow_run.project_id,
                flow_run_id=self.flow_run.id,
                artifact_type=stage.artifact_type,
                title=stage.artifact_title,
                content_markdown=markdown,
                content_json=execution.payload,
                source_task_run_id=task_run.id,
                version_no=1,
            )
            artifact = self.repository.create_artifact(artifact)
            self.state.artifact_ids.append(artifact.id)
            self._mark_run(state_json=self.state.model_dump(mode="json"))
            self._emit_event(
                "task.completed",
                stage.crew_name,
                {
                    "step_code": stage.step_code,
                    "artifact_uid": artifact.artifact_uid,
                    "runtime_mode": execution.runtime_mode,
                },
                task_run.id,
            )
        except Exception as exc:
            task_run.status = "FAILED"
            task_run.error_message = str(exc)
            task_run.finished_at = utc_now()
            self.repository.save_task(task_run)
            self._mark_run(
                status="FAILED",
                stage=stage.stage_name,
                error_message=str(exc),
                finished_at=utc_now(),
            )
            self._emit_event(
                "task.failed",
                stage.crew_name,
                {
                    "step_code": stage.step_code,
                    "error": str(exc),
                    "runtime_mode": self.runtime_mode,
                },
                task_run.id,
            )
            raise

    def _execute_stage(
        self,
        stage: StageDefinition,
        resolved_agent: ResolvedAgentProfile,
    ) -> StageExecutionResult:
        if self.runtime_mode == "template":
            payload = stage.handler(self.state)
            return StageExecutionResult(payload=payload, runtime_mode="template")

        crewai_result = self.crewai_runner.run_stage(
            crew_name=stage.crew_name,
            agent_profile=resolved_agent,
            task_description=resolved_agent.prompt_snapshot["task_description"],
            expected_output=stage.expected_output,
            output_model=stage.response_model,
        )
        structured_output = stage.response_model.model_validate(crewai_result.payload)
        payload = stage.apply_output(self.state, structured_output)
        return StageExecutionResult(
            payload=payload,
            runtime_mode="crewai",
            raw_output=crewai_result.raw_output,
            prompt_tokens=crewai_result.prompt_tokens,
            completion_tokens=crewai_result.completion_tokens,
        )

    def _resolve_runtime_mode(self) -> str:
        if settings.agent_runtime_mode == "template":
            return "template"

        if settings.agent_runtime_mode == "crewai":
            self._ensure_ai_runtime_ready()
            return "crewai"

        if settings.has_ai_runtime_config:
            return "crewai"
        return "template"

    def _ensure_ai_runtime_ready(self) -> None:
        if settings.has_ai_runtime_config:
            return

        raise RuntimeError(
            "AGENT_RUNTIME_MODE=crewai 但当前没有可用的模型运行配置。"
            "请设置 OPENAI_API_KEY，或把 OPENAI_BASE_URL 指向一个可用的 OpenAI 兼容端点。"
        )

    def _build_stage_context(self, stage: StageDefinition) -> Dict[str, Any]:
        snapshot = self.state.model_dump(
            mode="json",
            exclude={"artifact_ids"},
        )
        snapshot["target_stage"] = stage.step_code
        snapshot["artifact_title"] = stage.artifact_title
        return snapshot

    def _build_task_description(self, stage: StageDefinition) -> str:
        context_json = json.dumps(self._build_stage_context(stage), ensure_ascii=False, indent=2)
        lines = [
            f"You are executing the '{stage.step_code}' stage of the SE-Agent Studio technical design workflow.",
            f"Artifact to produce: {stage.artifact_title}.",
            f"Stage objective: {stage.goal}",
            "",
            "Project requirement:",
            self.state.requirement_text.strip(),
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

    def _extract_features(self) -> List[str]:
        base_text = self.state.requirement_text.replace("。", "\n").replace("；", "\n").replace(";", "\n")
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
        features = self._extract_features()
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

    def _render_markdown(self, title: str, payload: Dict[str, Any]) -> str:
        lines = [f"# {title}", ""]
        for key, value in payload.items():
            if key.startswith("_"):
                continue
            lines.append(f"## {key}")
            lines.append("")
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"- `{json.dumps(item, ensure_ascii=False)}`")
                    else:
                        lines.append(f"- {item}")
            elif isinstance(value, dict):
                lines.append("```json")
                lines.append(json.dumps(value, ensure_ascii=False, indent=2))
                lines.append("```")
            else:
                lines.append(str(value))
            lines.append("")
        return "\n".join(lines).strip()
