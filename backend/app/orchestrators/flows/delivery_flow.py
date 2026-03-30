from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.core.config import settings
from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
from app.orchestrators.flows.technical_design_flow import (
    PreparedStageExecution,
    StageDefinition,
    StageExecutionResult,
    StageTemplate,
    TechnicalDesignFlow,
)
from app.orchestrators.outputs.delivery_models import (
    CodeBundle,
    CommandSpec,
    DeliveryHandoff,
    DeliveryRequirementSpec,
    GeneratedFile,
    IntegrationBundle,
    SolutionDeliveryPlan,
    VerificationResult,
)
from app.orchestrators.outputs.flow_models import ProjectFlowState


DELIVERY_STAGE_TEMPLATE_REGISTRY: dict[str, StageTemplate] = {
    "delivery_requirements": StageTemplate(
        step_code="delivery_requirements",
        stage_name="delivery_requirements",
        crew_name="RequirementAnalysisCrew",
        default_agent_code="product_manager",
        artifact_type="delivery_requirements",
        artifact_title="交付需求规格",
        handler_name="_build_delivery_requirements",
        response_model=DeliveryRequirementSpec,
        goal="Turn the raw brief into a runnable starter-delivery scope with explicit acceptance criteria.",
        expected_output="Return a complete DeliveryRequirementSpec with concrete users, capabilities, acceptance criteria, and non-goals.",
        apply_output_name="_apply_delivery_requirements_output",
    ),
    "solution_design": StageTemplate(
        step_code="solution_design",
        stage_name="solution_design",
        crew_name="ArchitectureDesignCrew",
        default_agent_code="software_architect",
        artifact_type="solution_delivery_plan",
        artifact_title="交付实施方案",
        handler_name="_build_solution_design",
        response_model=SolutionDeliveryPlan,
        goal="Plan a concrete runnable starter project including stack, workspace layout, implementation order, and commands.",
        expected_output="Return a complete SolutionDeliveryPlan with stack choices, layout, implementation order, run commands, and validation commands.",
        apply_output_name="_apply_delivery_plan_output",
    ),
    "backend_delivery": StageTemplate(
        step_code="backend_delivery",
        stage_name="backend_delivery",
        crew_name="BackendDesignCrew",
        default_agent_code="backend_architect",
        artifact_type="backend_code_bundle",
        artifact_title="后端代码交付包",
        handler_name="_build_backend_delivery",
        response_model=CodeBundle,
        goal="Produce runnable backend starter files with API endpoints, local startup commands, and smoke tests.",
        expected_output="Return a complete CodeBundle with concrete backend files and commands.",
        apply_output_name="_apply_backend_delivery_output",
    ),
    "frontend_delivery": StageTemplate(
        step_code="frontend_delivery",
        stage_name="frontend_delivery",
        crew_name="FrontendDesignCrew",
        default_agent_code="frontend_developer",
        artifact_type="frontend_code_bundle",
        artifact_title="前端代码交付包",
        handler_name="_build_frontend_delivery",
        response_model=CodeBundle,
        goal="Produce runnable frontend starter files that integrate with the generated backend.",
        expected_output="Return a complete CodeBundle with concrete frontend files and commands.",
        apply_output_name="_apply_frontend_delivery_output",
    ),
    "integration": StageTemplate(
        step_code="integration",
        stage_name="integration",
        crew_name="QualityAssuranceCrew",
        default_agent_code="api_tester",
        artifact_type="integration_bundle",
        artifact_title="集成交付说明",
        handler_name="_build_integration",
        response_model=IntegrationBundle,
        goal="Merge the generated backend and frontend bundles into a real workspace and describe how to run and verify it.",
        expected_output="Return a complete IntegrationBundle with workspace root, generated files, startup steps, verification steps, and exposed endpoints.",
        apply_output_name="_apply_integration_output",
    ),
    "handoff": StageTemplate(
        step_code="handoff",
        stage_name="handoff",
        crew_name="ConsistencyReviewCrew",
        default_agent_code="software_architect",
        artifact_type="delivery_handoff",
        artifact_title="交付总结与移交",
        handler_name="_build_handoff",
        response_model=DeliveryHandoff,
        goal="Summarize the generated deliverable, startup guide, verification status, and next engineering steps.",
        expected_output="Return a complete DeliveryHandoff with generated assets, startup guide, verification status, and next steps.",
        apply_output_name="_apply_handoff_output",
    ),
}


class DeliveryFlow(TechnicalDesignFlow):
    stage_template_registry = DELIVERY_STAGE_TEMPLATE_REGISTRY
    flow_event_source = "DeliveryFlow"
    repairable_stage_codes = {"backend_delivery", "frontend_delivery"}
    managed_stage_codes = {"integration", "handoff"}
    max_repair_attempts = 2

    def _resolve_runtime_mode(self) -> str:
        if settings.agent_runtime_mode == "template":
            return "template"
        if settings.agent_runtime_mode == "crewai":
            self._ensure_ai_runtime_ready()
            return "crewai"
        if self.runtime_config or settings.has_ai_runtime_config:
            return "crewai"
        # delivery_v1 still guarantees a deterministic fallback when the user has not configured an AI runtime yet.
        return "template"

    def _execute_stage(
        self,
        stage: StageDefinition,
        resolved_agent: ResolvedAgentProfile,
        state: ProjectFlowState,
    ) -> StageExecutionResult:
        if stage.step_code in self.managed_stage_codes:
            payload = stage.handler(state)
            runtime_mode = "template" if self.runtime_mode == "template" else "crewai-hybrid"
            return StageExecutionResult(payload=payload, runtime_mode=runtime_mode)
        try:
            return super()._execute_stage(stage, resolved_agent, state)
        except Exception as exc:
            if self._should_fallback_to_template_bundle(stage, exc):
                payload = self._build_template_fallback_bundle(stage, state, exc)
                return StageExecutionResult(payload=payload, runtime_mode="template-fallback")
            raise

    def _complete_stage_execution(
        self,
        prepared: PreparedStageExecution,
        execution: StageExecutionResult,
    ) -> None:
        super()._complete_stage_execution(prepared, execution)
        if execution.runtime_mode == "template-fallback":
            self._emit_event(
                "delivery.stage_fallback",
                self.flow_event_source,
                {
                    "step_code": prepared.stage.step_code,
                    "runtime_mode": execution.runtime_mode,
                },
                prepared.task_run.id,
            )

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

        if stage.step_code == "delivery_requirements":
            context["intake_summary"] = {
                "brief_excerpt": self._truncate_text(active_state.requirement_text, 420),
                "feature_clues": self._extract_features(active_state),
            }
            return context

        context["delivery_requirements"] = self._summarize_delivery_requirements(active_state)

        if stage.step_code == "solution_design":
            return context

        context["delivery_plan"] = self._summarize_delivery_plan(active_state)

        if stage.step_code in {"backend_delivery", "frontend_delivery"}:
            return context

        if stage.step_code == "integration":
            context["backend_bundle"] = self._summarize_code_bundle(active_state.backend_code_bundle)
            context["frontend_bundle"] = self._summarize_code_bundle(active_state.frontend_code_bundle)
            return context

        if stage.step_code == "handoff":
            context["integration_bundle"] = self._summarize_integration_bundle(active_state)
            return context

        return context

    def _build_task_description(
        self,
        stage: StageDefinition,
        state: Optional[ProjectFlowState] = None,
    ) -> str:
        active_state = state or self.state
        context_json = json.dumps(self._build_stage_context(stage, active_state), ensure_ascii=False, indent=2)
        lines = [
            f"You are executing the '{stage.step_code}' stage of the SE-Agent Studio software delivery workflow.",
            f"Artifact to produce: {stage.artifact_title}.",
            f"Stage objective: {stage.goal}",
            "",
            "Original project brief:",
            self._truncate_text(active_state.requirement_text.strip(), 1200),
            "",
            "Current structured context JSON:",
            context_json,
            "",
            "Answer requirements:",
            "- Return only valid structured data for the requested schema.",
            "- When the schema includes files, every file must have a concrete path, language, purpose, and full content.",
            "- Produce runnable starter code instead of design-only prose.",
            "- Use concise Chinese for human-readable explanations because the project context is Chinese.",
            "- Avoid placeholders such as TBD, TODO, omitted, or same as above.",
        ]
        return "\n".join(lines).strip()

    def _summarize_delivery_requirements(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.delivery_requirements:
            return {
                "brief_excerpt": self._truncate_text(state.requirement_text.strip(), 240),
                "feature_clues": self._extract_features(state),
            }
        payload = state.delivery_requirements
        summary = {
            "app_name": payload.get("app_name", ""),
            "app_summary": self._truncate_text(payload.get("app_summary", ""), 120),
            "core_capabilities": self._compact_list(payload.get("core_capabilities"), limit=4),
            "acceptance_criteria": self._compact_list(payload.get("acceptance_criteria"), limit=3),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_delivery_plan(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.delivery_plan:
            return {}
        payload = state.delivery_plan
        summary = {
            "architecture_style": payload.get("architecture_style", ""),
            "stack_choices": self._compact_list(payload.get("stack_choices"), limit=4),
            "workspace_layout": self._compact_list(payload.get("workspace_layout"), limit=6),
            "implementation_order": self._compact_list(payload.get("implementation_order"), limit=4),
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_code_bundle(self, payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not payload:
            return {}
        file_paths = []
        for item in self._compact_list(payload.get("files"), limit=8):
            if isinstance(item, dict):
                file_paths.append(item.get("path", ""))
        summary = {
            "bundle_name": payload.get("bundle_name", ""),
            "entrypoints": self._compact_list(payload.get("entrypoints"), limit=3),
            "files": [path for path in file_paths if path],
        }
        return {key: value for key, value in summary.items() if value}

    def _summarize_integration_bundle(self, state: ProjectFlowState) -> Dict[str, Any]:
        if not state.integration_bundle:
            return {}
        payload = state.integration_bundle
        summary = {
            "workspace_root": payload.get("workspace_root", ""),
            "generated_files": self._compact_list(payload.get("generated_files"), limit=8),
            "startup_steps": self._compact_list(payload.get("startup_steps"), limit=4),
            "verification_overview": self._compact_list(self._verification_status_lines(payload.get("verification_results")), limit=3),
            "exposed_endpoints": self._compact_list(payload.get("exposed_endpoints"), limit=4),
        }
        return {key: value for key, value in summary.items() if value}

    def _apply_delivery_requirements_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = DeliveryRequirementSpec.model_validate(output)
        state.delivery_requirements = structured_output.model_dump(mode="json")
        return state.delivery_requirements

    def _apply_delivery_plan_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = SolutionDeliveryPlan.model_validate(output)
        state.delivery_plan = structured_output.model_dump(mode="json")
        return state.delivery_plan

    def _apply_backend_delivery_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = CodeBundle.model_validate(output)
        state.backend_code_bundle = structured_output.model_dump(mode="json")
        return state.backend_code_bundle

    def _apply_frontend_delivery_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = CodeBundle.model_validate(output)
        state.frontend_code_bundle = structured_output.model_dump(mode="json")
        return state.frontend_code_bundle

    def _apply_integration_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = IntegrationBundle.model_validate(output)
        state.integration_bundle = structured_output.model_dump(mode="json")
        return state.integration_bundle

    def _apply_handoff_output(self, state: ProjectFlowState, output: BaseModel) -> Dict[str, Any]:
        structured_output = DeliveryHandoff.model_validate(output)
        state.delivery_handoff = structured_output.model_dump(mode="json")
        return state.delivery_handoff

    def _build_delivery_requirements(self, state: ProjectFlowState) -> Dict[str, Any]:
        features = list(
            dict.fromkeys(
                [
                    *self._extract_features(state),
                    "浏览任务列表并查看当前状态",
                    "新增任务并立即刷新界面",
                    "切换任务完成状态",
                    "删除任务并回显结果",
                    "通过 /healthz 确认后端服务正常",
                ]
            )
        )[:6]
        spec = DeliveryRequirementSpec(
            app_name=self._derive_app_name(state),
            app_summary=self._truncate_text(state.requirement_text.strip(), 180),
            target_users=["项目发起人", "研发同学", "验收人员"],
            core_capabilities=features,
            acceptance_criteria=[
                "后端可以通过 uvicorn 本地启动并返回 /healthz 200",
                "前端可以通过静态服务器打开并正确调用后端 API",
                "用户可以完成任务的新增、完成状态切换和删除",
            ],
            non_goals=[
                "当前 starter 不包含鉴权、数据库迁移和生产部署脚本",
                "当前数据以内存存储，适合本地演示和二次开发起点",
            ],
        )
        state.delivery_requirements = spec.model_dump(mode="json")
        return state.delivery_requirements

    def _build_solution_design(self, state: ProjectFlowState) -> Dict[str, Any]:
        workspace_root = self._delivery_workspace_root()
        plan = SolutionDeliveryPlan(
            architecture_style="FastAPI API + 轻量前端页面 + 本地联调脚手架",
            stack_choices=[
                "后端使用 FastAPI + Uvicorn，提供最小 CRUD API",
                "前端使用原生 HTML / CSS / JavaScript，降低首次运行门槛",
                "数据先使用内存存储，保证 starter 零配置可运行",
                "验证方式使用 pytest + FastAPI TestClient",
            ],
            workspace_layout=[
                "README.md",
                "backend/main.py",
                "backend/requirements.txt",
                "backend/requirements-dev.txt",
                "backend/test_api.py",
                "frontend/index.html",
                "frontend/app.js",
                "frontend/styles.css",
            ],
            implementation_order=[
                "先生成后端健康检查与任务 CRUD API",
                "再生成前端页面与 fetch 调用逻辑",
                "最后写入工作区并补齐启动说明与测试命令",
            ],
            run_commands=self._solution_run_commands(workspace_root),
            validation_commands=self._solution_validation_commands(workspace_root),
            delivery_notes=[
                "delivery_v1 当前采用确定性 starter 生成，优先保证能跑起来",
                "后续可以把 backend_delivery / frontend_delivery 阶段替换为真实代码代理",
            ],
        )
        state.delivery_plan = plan.model_dump(mode="json")
        return state.delivery_plan

    def _build_backend_delivery(self, state: ProjectFlowState) -> Dict[str, Any]:
        app_name = self._state_value(state.delivery_requirements, "app_name", "交付演示应用")
        workspace_root = self._delivery_workspace_root()
        bundle = CodeBundle(
            bundle_name="FastAPI Backend Starter",
            summary=f"为 {app_name} 生成一个可本地启动的任务管理 API，包含健康检查、列表、新增、更新和删除接口。",
            runtime="python",
            entrypoints=["backend/main.py", "backend/test_api.py"],
            files=[
                GeneratedFile(
                    path="backend/requirements.txt",
                    language="text",
                    purpose="后端运行依赖",
                    content="fastapi==0.115.0\nuvicorn[standard]==0.32.0\npydantic==2.9.2\n",
                ),
                GeneratedFile(
                    path="backend/requirements-dev.txt",
                    language="text",
                    purpose="后端测试依赖",
                    content="-r requirements.txt\npytest==8.3.3\nhttpx==0.28.1\n",
                ),
                GeneratedFile(
                    path="backend/main.py",
                    language="python",
                    purpose="FastAPI 应用入口和任务 CRUD API",
                    content=self._backend_main_content(app_name),
                ),
                GeneratedFile(
                    path="backend/test_api.py",
                    language="python",
                    purpose="后端最小 smoke test",
                    content=self._backend_test_content(),
                ),
            ],
            run_commands=self._solution_run_commands(workspace_root)[:2],
            setup_notes=[
                "后端默认监听 http://127.0.0.1:8001",
                "当前任务数据保存在内存中，重启服务后会重置为默认样例",
            ],
        )
        state.backend_code_bundle = bundle.model_dump(mode="json")
        return state.backend_code_bundle

    def _build_frontend_delivery(self, state: ProjectFlowState) -> Dict[str, Any]:
        app_name = self._state_value(state.delivery_requirements, "app_name", "交付演示应用")
        workspace_root = self._delivery_workspace_root()
        bundle = CodeBundle(
            bundle_name="Frontend Starter",
            summary=f"为 {app_name} 生成一个可直接静态托管的任务看板页面，内置与 FastAPI 后端联调的 fetch 逻辑。",
            runtime="browser",
            entrypoints=["frontend/index.html", "frontend/app.js"],
            files=[
                GeneratedFile(
                    path="frontend/index.html",
                    language="html",
                    purpose="页面入口与结构骨架",
                    content=self._frontend_html_content(app_name),
                ),
                GeneratedFile(
                    path="frontend/app.js",
                    language="javascript",
                    purpose="任务列表渲染、表单提交和 API 调用逻辑",
                    content=self._frontend_js_content(app_name),
                ),
                GeneratedFile(
                    path="frontend/styles.css",
                    language="css",
                    purpose="任务看板页面样式",
                    content=self._frontend_css_content(),
                ),
            ],
            run_commands=self._solution_run_commands(workspace_root)[2:],
            setup_notes=[
                "前端默认假定后端 API 在 http://127.0.0.1:8001",
                "可以通过修改 frontend/app.js 中的 API_BASE 适配其他地址",
            ],
        )
        state.frontend_code_bundle = bundle.model_dump(mode="json")
        return state.frontend_code_bundle

    def _build_integration(self, state: ProjectFlowState) -> Dict[str, Any]:
        workspace_root, generated_files, materialized_files = self._materialize_workspace(state)
        verification_results = self._verify_generated_workspace(workspace_root)
        self._emit_verification_event(verification_results, attempt=0)
        repair_notes: List[str] = []

        if self.runtime_mode == "crewai" and any(not item.success for item in verification_results):
            (
                workspace_root,
                generated_files,
                materialized_files,
                verification_results,
                repair_notes,
            ) = self._run_delivery_repair_loop(
                state,
                verification_results,
            )

        bundle = IntegrationBundle(
            workspace_root=str(workspace_root),
            generated_files=generated_files,
            files=materialized_files,
            startup_steps=[
                f"进入工作区：cd '{workspace_root}'",
                f"安装后端依赖：cd '{workspace_root / 'backend'}' && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt",
                f"启动后端：cd '{workspace_root / 'backend'}' && source .venv/bin/activate && uvicorn main:app --reload --port 8001",
                f"启动前端：cd '{workspace_root / 'frontend'}' && python3 -m http.server 4173",
            ],
            verification_steps=[
                "访问 http://127.0.0.1:8001/healthz，确认返回 status=ok",
                "打开 http://127.0.0.1:4173，确认页面能加载任务列表",
                f"执行测试：cd '{workspace_root / 'backend'}' && source .venv/bin/activate && pip install -r requirements-dev.txt && pytest test_api.py",
            ],
            verification_results=verification_results,
            exposed_endpoints=[
                "GET /healthz",
                "GET /api/tasks",
                "POST /api/tasks",
                "PUT /api/tasks/{task_id}",
                "DELETE /api/tasks/{task_id}",
            ],
            notes=[
                "代码已经写入交付工作区，可直接进入对应路径继续开发",
                *repair_notes,
                self._verification_summary_note(verification_results),
                "当前 starter 聚焦最小可运行闭环，后续可接入数据库、鉴权和真实构建流程",
            ],
        )
        state.integration_bundle = bundle.model_dump(mode="json")
        return state.integration_bundle

    def _build_handoff(self, state: ProjectFlowState) -> Dict[str, Any]:
        workspace_root = self._state_value(state.integration_bundle, "workspace_root", str(self._delivery_workspace_root()))
        generated_assets = self._list_generated_assets(state)
        verification_results = self._verification_results_from_payload(state.integration_bundle)
        handoff = DeliveryHandoff(
            workspace_root=workspace_root,
            generated_assets=generated_assets,
            startup_guide=[
                f"工作区位置：{workspace_root}",
                "先启动 backend/main.py 对应的 FastAPI 服务，再启动 frontend 目录下的静态页面服务",
                "使用 backend/test_api.py 做最小回归，确认 CRUD API 没有被后续改动破坏",
            ],
            verification_status=self._verification_status_lines(verification_results),
            verification_results=verification_results,
            next_steps=[
                "把内存存储替换为 SQLite / PostgreSQL 持久化",
                "为前端增加构建工具链、环境变量和更完整的组件拆分",
                "把 delivery_v1 的模板阶段逐步替换成真实代码生成与测试修复代理",
            ],
        )
        state.delivery_handoff = handoff.model_dump(mode="json")
        return state.delivery_handoff

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

        placeholder_markers = ("tbd", "todo", "same as above", "待补充", "暂无")
        lowered_fragments = [item.lower() for item in text_fragments]
        matched_markers = sorted({marker for marker in placeholder_markers if any(marker in fragment for fragment in lowered_fragments)})
        if matched_markers:
            raise ValueError(
                f"阶段 {stage.step_code} 未通过质量门禁：检测到占位式表述 {', '.join(matched_markers)}。"
            )

        combined_length = sum(len(item) for item in text_fragments)
        min_text_length = {
            "delivery_requirements": 80,
            "solution_design": 100,
            "backend_delivery": 300,
            "frontend_delivery": 300,
            "integration": 80,
            "handoff": 60,
        }.get(stage.step_code, 80)
        if combined_length < min_text_length:
            raise ValueError(
                f"阶段 {stage.step_code} 未通过质量门禁：文本信息量不足，当前仅 {combined_length} 个字符。"
            )

        list_requirements = {
            "delivery_requirements": {
                "target_users": 1,
                "core_capabilities": 2,
                "acceptance_criteria": 2,
                "non_goals": 1,
            },
            "solution_design": {
                "stack_choices": 2,
                "workspace_layout": 4,
                "implementation_order": 2,
                "run_commands": 2,
                "validation_commands": 1,
            },
            "backend_delivery": {
                "entrypoints": 1,
                "files": 3,
                "run_commands": 1,
            },
            "frontend_delivery": {
                "entrypoints": 1,
                "files": 3,
                "run_commands": 1,
            },
            "integration": {
                "generated_files": 6,
                "files": 6,
                "startup_steps": 3,
                "verification_steps": 2,
                "verification_results": 2,
                "exposed_endpoints": 3,
            },
            "handoff": {
                "generated_assets": 4,
                "startup_guide": 2,
                "verification_status": 2,
                "verification_results": 2,
                "next_steps": 2,
            },
        }.get(stage.step_code, {})

        for path, minimum in list_requirements.items():
            self._assert_min_items(payload, path, minimum, stage.step_code)

        notes = [
            f"已通过交付质量门禁：识别到 {len(text_fragments)} 段文本，累计 {combined_length} 个字符。",
            f"当前运行模式：{runtime_mode}。",
        ]
        if stage.step_code in {"backend_delivery", "frontend_delivery"}:
            notes.append("当前阶段包含完整代码文件内容，可直接写入工作区继续开发。")
        if stage.step_code == "integration":
            notes.append("当前阶段已经把 starter 代码落盘到交付工作区，并执行了自动验证。")
        return notes

    def _render_delivery_requirements_markdown(self, payload: Dict[str, Any]) -> List[str]:
        return [
            "## 交付目标",
            "",
            f"**应用名称**：{payload.get('app_name', '')}",
            "",
            f"**简要说明**：{payload.get('app_summary', '')}",
            "",
            "## 目标用户",
            "",
            *self._render_bullet_list(payload.get("target_users", [])),
            "",
            "## 核心能力",
            "",
            *self._render_bullet_list(payload.get("core_capabilities", [])),
            "",
            "## 验收标准",
            "",
            *self._render_bullet_list(payload.get("acceptance_criteria", [])),
            "",
            "## 当前不做",
            "",
            *self._render_bullet_list(payload.get("non_goals", [])),
        ]

    def _render_solution_design_markdown(self, payload: Dict[str, Any]) -> List[str]:
        run_rows = self._command_rows(payload.get("run_commands", []))
        validation_rows = self._command_rows(payload.get("validation_commands", []))
        return [
            "## 实施架构",
            "",
            f"**交付方式**：{payload.get('architecture_style', '')}",
            "",
            "## 技术栈选择",
            "",
            *self._render_bullet_list(payload.get("stack_choices", [])),
            "",
            "## 工作区布局",
            "",
            *self._render_bullet_list(payload.get("workspace_layout", [])),
            "",
            "## 实施顺序",
            "",
            *self._render_numbered_list(payload.get("implementation_order", [])),
            "",
            "## 启动命令",
            "",
            *self._render_markdown_table(["步骤", "命令", "目的"], run_rows),
            "",
            "## 验证命令",
            "",
            *self._render_markdown_table(["步骤", "命令", "目的"], validation_rows),
            "",
            "## 交付备注",
            "",
            *self._render_bullet_list(payload.get("delivery_notes", [])),
        ]

    def _render_backend_delivery_markdown(self, payload: Dict[str, Any]) -> List[str]:
        return self._render_code_bundle_markdown(payload)

    def _render_frontend_delivery_markdown(self, payload: Dict[str, Any]) -> List[str]:
        return self._render_code_bundle_markdown(payload)

    def _render_integration_markdown(self, payload: Dict[str, Any]) -> List[str]:
        lines = [
            "## 工作区信息",
            "",
            f"**工作区路径**：`{payload.get('workspace_root', '')}`",
            "",
            "## 已生成文件",
            "",
            *self._render_bullet_list(payload.get("generated_files", [])),
            "",
            "## 启动步骤",
            "",
            *self._render_numbered_list(payload.get("startup_steps", [])),
            "",
            "## 验证步骤",
            "",
            *self._render_numbered_list(payload.get("verification_steps", [])),
            "",
            "## 自动验证结果",
            "",
            *self._render_verification_results_markdown(payload.get("verification_results", [])),
            "",
            "## 暴露接口",
            "",
            *self._render_bullet_list(payload.get("exposed_endpoints", [])),
            "",
            "## 集成说明",
            "",
            *self._render_bullet_list(payload.get("notes", [])),
        ]
        return lines

    def _render_handoff_markdown(self, payload: Dict[str, Any]) -> List[str]:
        lines = [
            "## 交付位置",
            "",
            f"**工作区路径**：`{payload.get('workspace_root', '')}`",
            "",
            "## 已生成资产",
            "",
            *self._render_bullet_list(payload.get("generated_assets", [])),
            "",
            "## 启动指南",
            "",
            *self._render_numbered_list(payload.get("startup_guide", [])),
            "",
            "## 当前验证状态",
            "",
            *self._render_bullet_list(payload.get("verification_status", [])),
            "",
            "## 验证详情",
            "",
            *self._render_verification_results_markdown(payload.get("verification_results", [])),
            "",
            "## 后续建议",
            "",
            *self._render_bullet_list(payload.get("next_steps", [])),
        ]
        return lines

    def _render_code_bundle_markdown(self, payload: Dict[str, Any]) -> List[str]:
        lines = [
            "## Bundle 概要",
            "",
            f"**名称**：{payload.get('bundle_name', '')}",
            "",
            f"**运行时**：{payload.get('runtime', '')}",
            "",
            f"**说明**：{payload.get('summary', '')}",
            "",
            "## 入口文件",
            "",
            *self._render_bullet_list(payload.get("entrypoints", [])),
            "",
            "## 启动命令",
            "",
            *self._render_markdown_table(["步骤", "命令", "目的"], self._command_rows(payload.get("run_commands", []))),
            "",
            "## 文件清单",
            "",
        ]

        for file_item in payload.get("files", []):
            if not isinstance(file_item, dict):
                continue
            lines.append(f"- `{file_item.get('path', '')}`：{file_item.get('purpose', '')}")

        lines.extend(["", "## 文件内容", ""])

        for file_item in payload.get("files", []):
            if not isinstance(file_item, dict):
                continue
            lines.extend(
                [
                    f"### `{file_item.get('path', '')}`",
                    "",
                    f"- **用途**：{file_item.get('purpose', '')}",
                    "",
                    f"```{file_item.get('language', '')}",
                    file_item.get("content", ""),
                    "```",
                    "",
                ]
            )

        lines.extend(["## 使用说明", ""])
        lines.extend(self._render_bullet_list(payload.get("setup_notes", [])))
        return lines

    def _command_rows(self, commands: List[Any]) -> List[List[str]]:
        rows: List[List[str]] = []
        for item in commands:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    item.get("label", ""),
                    item.get("command", ""),
                    item.get("purpose", ""),
                ]
            )
        return rows

    def _render_verification_results_markdown(self, results: List[Any]) -> List[str]:
        lines: List[str] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            status_label = "通过" if item.get("success") else "失败"
            lines.extend(
                [
                    f"### {item.get('label', '')}（{status_label}）",
                    "",
                    f"- **命令**：`{item.get('command', '')}`",
                    f"- **结论**：{item.get('summary', '')}",
                    f"- **退出码**：{item.get('exit_code', '')}",
                    "",
                    "```text",
                    item.get("output", ""),
                    "```",
                    "",
                ]
            )
        if not lines:
            return ["- 当前没有自动验证结果。"]
        return lines

    def _derive_app_name(self, state: ProjectFlowState) -> str:
        feature_clues = self._extract_features(state)
        if feature_clues:
            candidate = re.sub(r"[^\w\u4e00-\u9fff]+", "", feature_clues[0])[:16]
            if len(candidate) >= 4:
                return candidate
        return "交付演示工作台"

    def _delivery_workspace_root(self) -> Path:
        root = settings.repo_root / ".delivery-workspaces" / self.flow_run.run_uid
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _solution_run_commands(self, workspace_root: Path) -> List[CommandSpec]:
        backend_dir = workspace_root / "backend"
        frontend_dir = workspace_root / "frontend"
        return [
            CommandSpec(
                label="安装后端依赖",
                command=f"cd '{backend_dir}' && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt",
                purpose="准备 FastAPI 运行环境",
            ),
            CommandSpec(
                label="启动后端服务",
                command=f"cd '{backend_dir}' && source .venv/bin/activate && uvicorn main:app --reload --port 8001",
                purpose="启动 API 服务并暴露 CRUD 接口",
            ),
            CommandSpec(
                label="启动前端页面",
                command=f"cd '{frontend_dir}' && python3 -m http.server 4173",
                purpose="本地打开页面并联调后端 API",
            ),
        ]

    def _solution_validation_commands(self, workspace_root: Path) -> List[CommandSpec]:
        backend_dir = workspace_root / "backend"
        return [
            CommandSpec(
                label="健康检查",
                command="curl http://127.0.0.1:8001/healthz",
                purpose="确认后端服务正常响应",
            ),
            CommandSpec(
                label="运行后端测试",
                command=f"cd '{backend_dir}' && source .venv/bin/activate && pip install -r requirements-dev.txt && pytest test_api.py",
                purpose="验证核心 CRUD API 行为",
            ),
        ]

    def _materialize_workspace(self, state: ProjectFlowState) -> tuple[Path, List[str], List[GeneratedFile]]:
        workspace_root = self._delivery_workspace_root()
        if workspace_root.exists():
            shutil.rmtree(workspace_root)
        workspace_root.mkdir(parents=True, exist_ok=True)

        files: List[GeneratedFile] = []
        files.extend(self._bundle_files(state.backend_code_bundle))
        files.extend(self._bundle_files(state.frontend_code_bundle))
        files.extend(
            [
                GeneratedFile(
                    path="README.md",
                    language="md",
                    purpose="项目启动与联调说明",
                    content=self._workspace_readme_content(state, workspace_root),
                ),
                GeneratedFile(
                    path=".gitignore",
                    language="gitignore",
                    purpose="忽略本地环境产物",
                    content=".venv/\n__pycache__/\n*.pyc\n.DS_Store\n",
                ),
            ]
        )

        generated_files: List[str] = []
        for file_item in files:
            target = workspace_root / file_item.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(file_item.content, encoding="utf-8")
            generated_files.append(file_item.path)

        return workspace_root, generated_files, files

    def _bundle_files(self, payload: Optional[Dict[str, Any]]) -> List[GeneratedFile]:
        files: List[GeneratedFile] = []
        if not payload:
            return files
        for item in payload.get("files", []):
            if not isinstance(item, dict):
                continue
            files.append(GeneratedFile.model_validate(item))
        return files

    def _workspace_readme_content(self, state: ProjectFlowState, workspace_root: Path) -> str:
        app_name = self._state_value(state.delivery_requirements, "app_name", "交付演示工作台")
        run_commands = self._solution_run_commands(workspace_root)
        validation_commands = self._solution_validation_commands(workspace_root)
        lines = [
            f"# {app_name}",
            "",
            "这是由 SE-Agent Studio `delivery_v1` 工作流生成的可运行 starter 项目。",
            "",
            "## 目录",
            "",
            "- `backend/`: FastAPI API 与 smoke test",
            "- `frontend/`: 静态页面与 fetch 联调逻辑",
            "",
            "## 启动步骤",
            "",
        ]
        lines.extend([f"{index}. `{item.command}`" for index, item in enumerate(run_commands, start=1)])
        lines.extend(["", "## 验证步骤", ""])
        lines.extend([f"{index}. `{item.command}`" for index, item in enumerate(validation_commands, start=1)])
        lines.extend(
            [
                "",
                "## 当前说明",
                "",
                "- 这是一个本地演示友好的 starter，适合作为进一步接入数据库、鉴权和构建工具链的起点。",
                "- 当前任务数据使用内存存储，重启后端后会恢复默认样例。",
            ]
        )
        return "\n".join(lines).strip() + "\n"

    def _backend_main_content(self, app_name: str) -> str:
        return dedent(
            f"""
            from typing import List

            from fastapi import FastAPI, HTTPException, Response, status
            from fastapi.middleware.cors import CORSMiddleware
            from pydantic import BaseModel, Field


            app = FastAPI(title="{app_name} API")

            app.add_middleware(
                CORSMiddleware,
                allow_origins=[
                    "http://127.0.0.1:4173",
                    "http://localhost:4173",
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                ],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )


            class TaskBase(BaseModel):
                title: str = Field(min_length=1, max_length=120)
                done: bool = False


            class TaskCreate(TaskBase):
                pass


            class TaskUpdate(BaseModel):
                title: str = Field(min_length=1, max_length=120)
                done: bool


            class Task(TaskBase):
                id: int


            TASKS: List[Task] = [
                Task(id=1, title="梳理交付范围", done=True),
                Task(id=2, title="跑通后端 API", done=False),
                Task(id=3, title="联调前端页面", done=False),
            ]
            NEXT_ID = 4


            @app.get("/healthz")
            def healthz() -> dict[str, str]:
                return {{"status": "ok"}}


            @app.get("/api/tasks", response_model=List[Task])
            def list_tasks() -> List[Task]:
                return TASKS


            @app.post("/api/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
            def create_task(payload: TaskCreate) -> Task:
                global NEXT_ID
                task = Task(id=NEXT_ID, **payload.model_dump())
                TASKS.append(task)
                NEXT_ID += 1
                return task


            @app.put("/api/tasks/{{task_id}}", response_model=Task)
            def update_task(task_id: int, payload: TaskUpdate) -> Task:
                for index, existing in enumerate(TASKS):
                    if existing.id == task_id:
                        updated = Task(id=task_id, **payload.model_dump())
                        TASKS[index] = updated
                        return updated
                raise HTTPException(status_code=404, detail="Task not found")


            @app.delete("/api/tasks/{{task_id}}", status_code=status.HTTP_204_NO_CONTENT)
            def delete_task(task_id: int) -> Response:
                for index, existing in enumerate(TASKS):
                    if existing.id == task_id:
                        TASKS.pop(index)
                        return Response(status_code=status.HTTP_204_NO_CONTENT)
                raise HTTPException(status_code=404, detail="Task not found")
            """
        ).strip() + "\n"

    def _backend_test_content(self) -> str:
        return dedent(
            """
            from fastapi.testclient import TestClient

            from main import app


            client = TestClient(app)


            def test_healthz() -> None:
                response = client.get("/healthz")
                assert response.status_code == 200
                assert response.json()["status"] == "ok"


            def test_task_crud_roundtrip() -> None:
                created = client.post("/api/tasks", json={"title": "新增验收任务", "done": False})
                assert created.status_code == 201
                task_id = created.json()["id"]

                updated = client.put(f"/api/tasks/{task_id}", json={"title": "新增验收任务", "done": True})
                assert updated.status_code == 200
                assert updated.json()["done"] is True

                deleted = client.delete(f"/api/tasks/{task_id}")
                assert deleted.status_code == 204
            """
        ).strip() + "\n"

    def _frontend_html_content(self, app_name: str) -> str:
        return dedent(
            f"""
            <!doctype html>
            <html lang="zh-CN">
              <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>{app_name}</title>
                <link rel="stylesheet" href="./styles.css" />
              </head>
              <body>
                <main class="shell">
                  <section class="hero">
                    <p class="eyebrow">SE-Agent Studio Delivery</p>
                    <h1>{app_name}</h1>
                    <p class="hero-copy">这是一个由 delivery_v1 工作流生成的前端 starter，默认联调本地 FastAPI API。</p>
                    <div class="status-bar">
                      <span id="healthBadge" class="badge">等待检查后端</span>
                      <span class="badge badge--muted">API_BASE: http://127.0.0.1:8001</span>
                    </div>
                  </section>

                  <section class="panel">
                    <form id="taskForm" class="task-form">
                      <input id="taskInput" type="text" placeholder="输入一个任务，例如：补数据库持久化" maxlength="120" />
                      <button type="submit">新增任务</button>
                    </form>

                    <div class="panel-header">
                      <h2>任务清单</h2>
                      <button id="refreshButton" class="ghost-button" type="button">刷新</button>
                    </div>

                    <ul id="taskList" class="task-list"></ul>
                  </section>
                </main>

                <template id="taskItemTemplate">
                  <li class="task-item">
                    <label class="task-check">
                      <input type="checkbox" />
                      <span class="task-title"></span>
                    </label>
                    <button class="ghost-button task-delete" type="button">删除</button>
                  </li>
                </template>

                <script src="./app.js" type="module"></script>
              </body>
            </html>
            """
        ).strip() + "\n"

    def _frontend_js_content(self, app_name: str) -> str:
        return dedent(
            f"""
            const API_BASE = "http://127.0.0.1:8001";

            const healthBadge = document.getElementById("healthBadge");
            const taskForm = document.getElementById("taskForm");
            const taskInput = document.getElementById("taskInput");
            const taskList = document.getElementById("taskList");
            const refreshButton = document.getElementById("refreshButton");
            const taskItemTemplate = document.getElementById("taskItemTemplate");

            async function request(path, options = {{}}) {{
              const response = await fetch(`${{API_BASE}}${{path}}`, {{
                headers: {{
                  "Content-Type": "application/json",
                  ...(options.headers || {{}}),
                }},
                ...options,
              }});

              if (!response.ok) {{
                const text = await response.text();
                throw new Error(text || `Request failed: ${{response.status}}`);
              }}

              if (response.status === 204) {{
                return null;
              }}

              return response.json();
            }}

            async function checkHealth() {{
              try {{
                const result = await request("/healthz");
                healthBadge.textContent = `后端状态：${{result.status}}`;
                healthBadge.classList.add("badge--success");
              }} catch (error) {{
                healthBadge.textContent = "后端未启动";
                healthBadge.classList.remove("badge--success");
                console.error(error);
              }}
            }}

            function renderTasks(tasks) {{
              taskList.innerHTML = "";
              tasks.forEach((task) => {{
                const fragment = taskItemTemplate.content.cloneNode(true);
                const item = fragment.querySelector(".task-item");
                const checkbox = fragment.querySelector("input");
                const title = fragment.querySelector(".task-title");
                const deleteButton = fragment.querySelector(".task-delete");

                title.textContent = task.title;
                checkbox.checked = task.done;
                item.dataset.id = String(task.id);
                item.classList.toggle("is-done", task.done);

                checkbox.addEventListener("change", async () => {{
                  await request(`/api/tasks/${{task.id}}`, {{
                    method: "PUT",
                    body: JSON.stringify({{ title: task.title, done: checkbox.checked }}),
                  }});
                  await loadTasks();
                }});

                deleteButton.addEventListener("click", async () => {{
                  await request(`/api/tasks/${{task.id}}`, {{ method: "DELETE" }});
                  await loadTasks();
                }});

                taskList.appendChild(fragment);
              }});
            }}

            async function loadTasks() {{
              const tasks = await request("/api/tasks");
              renderTasks(tasks);
            }}

            taskForm.addEventListener("submit", async (event) => {{
              event.preventDefault();
              const title = taskInput.value.trim();
              if (!title) {{
                return;
              }}

              await request("/api/tasks", {{
                method: "POST",
                body: JSON.stringify({{ title, done: false }}),
              }});
              taskInput.value = "";
              await loadTasks();
            }});

            refreshButton.addEventListener("click", loadTasks);

            checkHealth();
            loadTasks().catch((error) => {{
              console.error("Failed to load tasks for {app_name}", error);
            }});
            """
        ).strip() + "\n"

    def _frontend_css_content(self) -> str:
        return dedent(
            """
            :root {
              color-scheme: light;
              --bg: #f5f1e8;
              --panel: rgba(255, 252, 247, 0.82);
              --line: rgba(48, 38, 24, 0.12);
              --ink: #221a12;
              --muted: #6e6254;
              --accent: #c95b2b;
              --accent-deep: #8f3310;
              --success: #1b7f5b;
            }

            * {
              box-sizing: border-box;
            }

            body {
              margin: 0;
              font-family: "Helvetica Neue", "PingFang SC", sans-serif;
              color: var(--ink);
              background:
                radial-gradient(circle at top left, rgba(201, 91, 43, 0.16), transparent 28%),
                radial-gradient(circle at bottom right, rgba(34, 26, 18, 0.1), transparent 32%),
                var(--bg);
              min-height: 100vh;
            }

            .shell {
              width: min(960px, calc(100vw - 32px));
              margin: 0 auto;
              padding: 40px 0 56px;
            }

            .hero,
            .panel {
              background: var(--panel);
              border: 1px solid var(--line);
              border-radius: 24px;
              backdrop-filter: blur(16px);
              box-shadow: 0 24px 48px rgba(34, 26, 18, 0.08);
            }

            .hero {
              padding: 28px;
              margin-bottom: 20px;
            }

            .eyebrow {
              margin: 0 0 10px;
              font-size: 12px;
              letter-spacing: 0.18em;
              text-transform: uppercase;
              color: var(--muted);
            }

            h1,
            h2,
            p {
              margin: 0;
            }

            h1 {
              font-size: clamp(2rem, 5vw, 3.4rem);
              line-height: 1;
            }

            .hero-copy {
              margin-top: 12px;
              max-width: 680px;
              color: var(--muted);
              line-height: 1.6;
            }

            .status-bar {
              display: flex;
              gap: 10px;
              flex-wrap: wrap;
              margin-top: 18px;
            }

            .badge {
              display: inline-flex;
              align-items: center;
              padding: 8px 12px;
              border-radius: 999px;
              background: rgba(201, 91, 43, 0.12);
              color: var(--accent-deep);
              font-size: 13px;
            }

            .badge--muted {
              background: rgba(34, 26, 18, 0.08);
              color: var(--muted);
            }

            .badge--success {
              background: rgba(27, 127, 91, 0.14);
              color: var(--success);
            }

            .panel {
              padding: 24px;
            }

            .task-form {
              display: grid;
              grid-template-columns: 1fr auto;
              gap: 12px;
            }

            .task-form input {
              height: 48px;
              border-radius: 14px;
              border: 1px solid var(--line);
              padding: 0 14px;
              font-size: 15px;
              background: rgba(255, 255, 255, 0.72);
            }

            button {
              height: 48px;
              border: 0;
              border-radius: 14px;
              padding: 0 16px;
              font-size: 15px;
              cursor: pointer;
              background: var(--accent);
              color: #fff8f1;
            }

            .ghost-button {
              height: 36px;
              background: rgba(34, 26, 18, 0.08);
              color: var(--ink);
            }

            .panel-header {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 16px;
              margin: 24px 0 16px;
            }

            .task-list {
              list-style: none;
              padding: 0;
              margin: 0;
              display: grid;
              gap: 12px;
            }

            .task-item {
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 16px;
              padding: 16px 18px;
              border-radius: 18px;
              border: 1px solid var(--line);
              background: rgba(255, 255, 255, 0.7);
            }

            .task-check {
              display: flex;
              align-items: center;
              gap: 12px;
            }

            .task-title {
              font-size: 15px;
            }

            .task-item.is-done .task-title {
              color: var(--muted);
              text-decoration: line-through;
            }

            @media (max-width: 720px) {
              .shell {
                width: min(100vw - 20px, 960px);
                padding-top: 20px;
              }

              .task-form {
                grid-template-columns: 1fr;
              }

              .panel-header,
              .task-item {
                flex-direction: column;
                align-items: stretch;
              }
            }
            """
        ).strip() + "\n"

    def _state_value(self, payload: Optional[Dict[str, Any]], key: str, default: str) -> str:
        if not payload:
            return default
        value = payload.get(key)
        return value if isinstance(value, str) and value.strip() else default

    def _stage_by_step_code(self, step_code: str) -> StageDefinition:
        for stage in self.stages:
            if stage.step_code == step_code:
                return stage
        raise ValueError(f"delivery_v1 未找到阶段定义: {step_code}")

    def _should_fallback_to_template_bundle(self, stage: StageDefinition, exc: Exception) -> bool:
        if self.runtime_mode != "crewai":
            return False
        if stage.step_code not in self.repairable_stage_codes:
            return False
        message = str(exc).lower()
        fallback_markers = (
            "invalid json",
            "json_invalid",
            "eof while parsing",
            "unterminated string",
            "expecting ',' delimiter",
        )
        return any(marker in message for marker in fallback_markers)

    def _build_template_fallback_bundle(
        self,
        stage: StageDefinition,
        state: ProjectFlowState,
        exc: Exception,
    ) -> Dict[str, Any]:
        payload = stage.handler(state)
        if isinstance(payload.get("setup_notes"), list):
            payload["setup_notes"].append(
                f"当前阶段的云端模型输出被截断，系统已自动回退到稳定 starter 模板。原因：{self._truncate_text(str(exc), 180)}"
            )
        if isinstance(payload.get("summary"), str) and payload["summary"].strip():
            payload["summary"] = payload["summary"].strip() + " 当前阶段已触发自动模板回退，以保证交付闭环继续完成。"
        return payload

    def _run_delivery_repair_loop(
        self,
        state: ProjectFlowState,
        verification_results: List[VerificationResult],
    ) -> tuple[Path, List[str], List[GeneratedFile], List[VerificationResult], List[str]]:
        workspace_root = self._delivery_workspace_root()
        generated_files: List[str] = []
        materialized_files: List[GeneratedFile] = []
        repair_notes: List[str] = []
        current_results = verification_results

        for attempt in range(1, self.max_repair_attempts + 1):
            repair_targets = self._repair_stage_codes_for_results(current_results)
            if not repair_targets:
                break

            target_labels = [self._repair_stage_label(step_code) for step_code in repair_targets]
            self._emit_event(
                "delivery.repair.started",
                self.flow_event_source,
                {
                    "attempt": attempt,
                    "targets": target_labels,
                    "failed_checks": [item.label for item in current_results if not item.success],
                },
            )

            for stage_code in repair_targets:
                stage_failures = [item for item in current_results if self._result_belongs_to_stage(item, stage_code)]
                repaired_payload = self._repair_code_bundle_with_ai(
                    stage_code=stage_code,
                    state=state,
                    failed_results=stage_failures,
                )
                if stage_code == "backend_delivery":
                    state.backend_code_bundle = repaired_payload
                elif stage_code == "frontend_delivery":
                    state.frontend_code_bundle = repaired_payload

            workspace_root, generated_files, materialized_files = self._materialize_workspace(state)
            current_results = self._verify_generated_workspace(workspace_root)
            self._emit_verification_event(current_results, attempt=attempt)
            self._emit_event(
                "delivery.repair.completed",
                self.flow_event_source,
                {
                    "attempt": attempt,
                    "targets": target_labels,
                    "passed_checks": sum(1 for item in current_results if item.success),
                    "total_checks": len(current_results),
                },
            )

            passed = sum(1 for item in current_results if item.success)
            repair_notes.append(
                f"第 {attempt} 轮自动修复已执行：{', '.join(target_labels)}。当前自动验证通过 {passed}/{len(current_results)} 项。"
            )
            if all(item.success for item in current_results):
                break

        return workspace_root, generated_files, materialized_files, current_results, repair_notes

    def _repair_stage_codes_for_results(self, results: List[VerificationResult]) -> List[str]:
        targets: List[str] = []
        for item in results:
            if item.success:
                continue
            if item.label.startswith("后端"):
                targets.append("backend_delivery")
                continue
            if item.label.startswith("前端"):
                targets.append("frontend_delivery")
        deduplicated: List[str] = []
        for item in targets:
            if item not in deduplicated:
                deduplicated.append(item)
        return deduplicated

    def _repair_code_bundle_with_ai(
        self,
        *,
        stage_code: str,
        state: ProjectFlowState,
        failed_results: List[VerificationResult],
    ) -> Dict[str, Any]:
        stage = self._stage_by_step_code(stage_code)
        current_bundle = state.backend_code_bundle if stage_code == "backend_delivery" else state.frontend_code_bundle
        partner_bundle = state.frontend_code_bundle if stage_code == "backend_delivery" else state.backend_code_bundle
        if not current_bundle:
            raise ValueError(f"阶段 {stage_code} 当前没有可修复的代码包。")

        repair_context = self._build_stage_context(stage, state)
        repair_context["current_bundle"] = current_bundle
        repair_context["partner_bundle_summary"] = self._summarize_code_bundle(partner_bundle)
        repair_context["verification_failures"] = [item.model_dump(mode="json") for item in failed_results]
        task_description = self._build_repair_task_description(
            stage=stage,
            state=state,
            current_bundle=current_bundle,
            partner_bundle=partner_bundle,
            failed_results=failed_results,
        )
        resolved_agent = self.agent_factory.resolve(
            agent_code=stage.agent_code,
            task_description=task_description,
            context=repair_context,
        )
        crewai_result = self.crewai_runner.run_stage(
            crew_name=stage.crew_name,
            agent_profile=resolved_agent,
            task_description=resolved_agent.prompt_snapshot["task_description"],
            expected_output=(
                f"{stage.expected_output} "
                "You are repairing an existing bundle, so return the full corrected CodeBundle with every file content included."
            ),
            output_model=stage.response_model,
        )
        structured_output = stage.response_model.model_validate(crewai_result.payload)
        payload = structured_output.model_dump(mode="json")
        self._validate_stage_payload_quality(stage, payload, runtime_mode="crewai-repair")
        return payload

    def _build_repair_task_description(
        self,
        *,
        stage: StageDefinition,
        state: ProjectFlowState,
        current_bundle: Dict[str, Any],
        partner_bundle: Optional[Dict[str, Any]],
        failed_results: List[VerificationResult],
    ) -> str:
        lines = [
            f"You are repairing the '{stage.step_code}' code bundle inside the SE-Agent Studio delivery workflow.",
            f"Artifact to return: {stage.artifact_title}.",
            f"Stage objective: {stage.goal}",
            "",
            "Original project brief:",
            self._truncate_text(state.requirement_text.strip(), 1200),
            "",
            "Delivery requirements summary:",
            json.dumps(self._summarize_delivery_requirements(state), ensure_ascii=False, indent=2),
            "",
            "Delivery plan summary:",
            json.dumps(self._summarize_delivery_plan(state), ensure_ascii=False, indent=2),
            "",
            "Current bundle JSON:",
            json.dumps(current_bundle, ensure_ascii=False, indent=2),
            "",
            "Companion bundle summary:",
            json.dumps(self._summarize_code_bundle(partner_bundle), ensure_ascii=False, indent=2),
            "",
            "Verification failures to fix:",
            json.dumps([item.model_dump(mode="json") for item in failed_results], ensure_ascii=False, indent=2),
            "",
            "Repair requirements:",
            "- Return a complete CodeBundle, not a diff.",
            "- Keep working files unless a change is required to fix the verification failure.",
            "- Preserve existing file paths when possible so the workspace layout stays stable.",
            "- Fix the concrete failing checks shown above instead of rewriting the whole project from scratch.",
            "- Use concise Chinese for human-readable text fields.",
            "- Avoid placeholders such as TBD, TODO, omitted, or same as above.",
        ]
        return "\n".join(lines).strip()

    def _repair_stage_label(self, stage_code: str) -> str:
        labels = {
            "backend_delivery": "后端交付",
            "frontend_delivery": "前端交付",
        }
        return labels.get(stage_code, stage_code)

    def _result_belongs_to_stage(self, result: VerificationResult, stage_code: str) -> bool:
        if stage_code == "backend_delivery":
            return result.label.startswith("后端")
        if stage_code == "frontend_delivery":
            return result.label.startswith("前端")
        return False

    def _emit_verification_event(self, results: List[VerificationResult], *, attempt: int) -> None:
        self._emit_event(
            "delivery.verification.completed",
            self.flow_event_source,
            {
                "attempt": attempt,
                "passed_checks": sum(1 for item in results if item.success),
                "total_checks": len(results),
                "failed_checks": [item.label for item in results if not item.success],
            },
        )

    def _verify_generated_workspace(self, workspace_root: Path) -> List[VerificationResult]:
        backend_dir = workspace_root / "backend"
        frontend_dir = workspace_root / "frontend"
        return [
            self._run_verification_command(
                label="后端 pytest smoke",
                command=[sys.executable, "-m", "pytest", "test_api.py"],
                cwd=backend_dir,
                success_summary="后端 smoke test 已通过，CRUD API 可以在本地环境直接回归。",
                failure_summary="后端 smoke test 未通过，请优先查看输出并修复 main.py 或 test_api.py。",
                extra_env={"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
            ),
            self._run_verification_command(
                label="前端静态契约检查",
                command=[sys.executable, "-c", self._frontend_contract_check_script()],
                cwd=frontend_dir,
                success_summary="前端入口文件、样式文件和 API 调用脚本结构完整。",
                failure_summary="前端静态契约检查未通过，请查看 index.html / app.js / styles.css 的输出差异。",
            ),
        ]

    def _run_verification_command(
        self,
        *,
        label: str,
        command: List[str],
        cwd: Path,
        success_summary: str,
        failure_summary: str,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> VerificationResult:
        env = None
        if extra_env:
            env = os.environ.copy()
            env.update(extra_env)
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=45,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            output = self._trim_verification_output((exc.stdout or "") + "\n" + (exc.stderr or ""))
            return VerificationResult(
                label=label,
                command=shlex.join(command),
                success=False,
                exit_code=124,
                summary=f"{failure_summary} 该检查在 45 秒内没有完成。",
                output=output or "Command timed out without output.",
            )

        output = self._trim_verification_output((completed.stdout or "").strip() + "\n" + (completed.stderr or "").strip())
        if not output.strip():
            output = "Command finished without additional output."
        return VerificationResult(
            label=label,
            command=shlex.join(command),
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            summary=success_summary if completed.returncode == 0 else failure_summary,
            output=output,
        )

    def _frontend_contract_check_script(self) -> str:
        return dedent(
            """
            from pathlib import Path

            html = Path("index.html").read_text(encoding="utf-8")
            js = Path("app.js").read_text(encoding="utf-8")
            css_exists = Path("styles.css").exists()

            checks = {
                "task_form": 'id="taskForm"' in html,
                "task_list": 'id="taskList"' in html,
                "module_script": 'src="./app.js"' in html,
                "api_base": 'const API_BASE = "http://127.0.0.1:8001";' in js,
                "tasks_route": '"/api/tasks"' in js,
                "styles_css": css_exists,
            }
            missing = [name for name, passed in checks.items() if not passed]
            if missing:
                raise SystemExit("Missing checks: " + ", ".join(missing))
            print("Frontend contract checks passed:", ", ".join(checks))
            """
        ).strip()

    def _trim_verification_output(self, output: str, limit: int = 1800) -> str:
        normalized = output.strip()
        if len(normalized) <= limit:
            return normalized
        return normalized[:limit].rstrip() + "\n...<truncated>"

    def _verification_results_from_payload(self, payload: Optional[Dict[str, Any]]) -> List[VerificationResult]:
        if not payload:
            return []
        values = payload.get("verification_results")
        if not isinstance(values, list):
            return []
        results: List[VerificationResult] = []
        for item in values:
            if not isinstance(item, dict):
                continue
            results.append(VerificationResult.model_validate(item))
        return results

    def _verification_summary_note(self, results: List[VerificationResult]) -> str:
        passed = sum(1 for item in results if item.success)
        total = len(results)
        if total == 0:
            return "当前流程尚未生成自动验证结果。"
        if passed == total:
            return f"流程内自动验证已执行 {total} 项，全部通过。"
        return f"流程内自动验证已执行 {total} 项，其中 {passed} 项通过、{total - passed} 项失败。"

    def _verification_status_lines(self, values: Any) -> List[str]:
        results: List[VerificationResult] = []
        if isinstance(values, list):
            for item in values:
                if isinstance(item, VerificationResult):
                    results.append(item)
                elif isinstance(item, dict):
                    results.append(VerificationResult.model_validate(item))

        passed = sum(1 for item in results if item.success)
        total = len(results)
        lines = ["已生成本地可运行 starter 代码。"]
        if total:
            lines.append(f"自动验证已执行 {total} 项，当前通过 {passed} 项。")
        else:
            lines.append("当前还没有自动验证结果。")
        for item in results:
            outcome = "通过" if item.success else "失败"
            lines.append(f"{item.label}：{outcome}（exit={item.exit_code}）")
        lines.append("当前实现以本地演示为目标，数据保存在内存中。")
        return lines

    def _list_generated_assets(self, state: ProjectFlowState) -> List[str]:
        if state.integration_bundle and isinstance(state.integration_bundle.get("generated_files"), list):
            values = [str(item) for item in state.integration_bundle["generated_files"]]
            if values:
                return values
        return [
            "README.md",
            "backend/main.py",
            "backend/test_api.py",
            "frontend/index.html",
            "frontend/app.js",
            "frontend/styles.css",
        ]
