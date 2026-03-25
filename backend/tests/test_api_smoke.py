from __future__ import annotations

import importlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from threading import Event
from types import SimpleNamespace

from fastapi.testclient import TestClient


def build_client(db_path: Path, extra_env: dict[str, str] | None = None) -> TestClient:
    defaults = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "AUTO_CREATE_SCHEMA": "true",
        "BOOTSTRAP_DATA_ON_STARTUP": "true",
        "DEFAULT_OWNER_PASSWORD": "ChangeMe123!",
        "JWT_SECRET": "0123456789abcdef0123456789abcdef",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "AGENT_RUNTIME_MODE": "template",
        "EXECUTION_MODE": "thread",
    }
    for key, value in defaults.items():
        os.environ[key] = value
    for key, value in (extra_env or {}).items():
        os.environ[key] = value

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    module = importlib.import_module("app.main")
    return TestClient(module.app)


def login_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@se-agent.studio", "password": "ChangeMe123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_project(client: TestClient, headers: dict[str, str], name: str, latest_requirement: str) -> str:
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={
            "name": name,
            "description": f"{name} 描述",
            "latest_requirement": latest_requirement,
        },
    )
    assert project.status_code == 201
    return project.json()["uid"]


def wait_for_run_completion(client: TestClient, headers: dict[str, str], run_uid: str) -> str | None:
    final_status = None
    for _ in range(30):
        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        assert current.status_code == 200
        final_status = current.json()["status"]
        if final_status in {"COMPLETED", "FAILED", "CANCELLED"}:
            break
        time.sleep(0.2)
    return final_status


def build_crewai_payloads() -> dict[str, dict]:
    return {
        "RequirementAnalysisCrew": {
            "requirement_spec": {
                "project_name": "SE-Agent Studio",
                "problem_statement": "需要一个多智能体软件工程工作台。",
                "target_users": ["学生", "教师", "管理员"],
                "core_features": ["创建项目", "启动运行", "查看产物"],
                "non_functional_requirements": ["结构化输出", "可追踪"],
                "constraints": ["固定流程", "FastAPI + Vue"],
                "assumptions": ["单租户课程场景"],
                "open_questions": ["是否启用人工审核"],
            },
            "task_breakdown": {
                "milestones": [
                    {
                        "title": "需求结构化",
                        "owner_role": "Product Manager",
                        "objective": "固化需求",
                        "deliverable": "RequirementSpec",
                    }
                ],
                "priorities": ["先打通主链路"],
                "clarification_list": ["明确部署环境"],
            },
        },
        "ArchitectureDesignCrew": {
            "architecture_style": "模块化单体",
            "core_modules": ["API", "Flow", "Worker", "Frontend"],
            "data_flow": ["用户提交需求 -> 生成产物"],
            "deployment_units": ["web-api", "worker", "mysql", "redis", "frontend"],
            "key_decisions": ["Flow 管总控", "Schema First"],
            "risks": ["模型成本"],
            "adrs": [
                {
                    "title": "ADR-001",
                    "decision": "优先单体",
                    "rationale": "便于课程项目推进",
                    "trade_off": "扩展性一般",
                }
            ],
        },
        "BackendDesignCrew": {
            "service_boundary": ["项目服务", "运行服务"],
            "entities": [
                {
                    "name": "project",
                    "purpose": "项目上下文",
                    "key_fields": ["uid", "name"],
                }
            ],
            "api_contracts": [
                {
                    "method": "POST",
                    "path": "/api/v1/projects/{project_uid}/runs",
                    "summary": "创建运行",
                    "request_shape": "RunCreate",
                    "response_shape": "FlowRunDetail",
                }
            ],
            "async_strategy": ["Celery + Redis"],
            "observability": ["run_event", "task_run"],
            "risks": ["需要更多权限隔离"],
        },
        "FrontendDesignCrew": {
            "page_tree": [
                {
                    "page_name": "项目列表",
                    "goal": "查看和创建项目",
                    "key_sections": ["项目卡片", "最近活动"],
                }
            ],
            "component_map": ["ShellLayout", "ArtifactPanel"],
            "state_slices": ["authStore", "runStore"],
            "api_bindings": ["GET /api/v1/projects"],
            "realtime_strategy": ["优先 SSE"],
        },
        "AIPlatformDesignCrew": {
            "provider_strategy": ["OpenAI 兼容接口"],
            "model_policy": ["按 agent_profile 选择模型"],
            "prompt_policy": ["运行时固化 prompt 快照"],
            "output_schemas": ["RequirementSpec", "ArchitectureBlueprint"],
            "evaluation_plan": ["校验字段完整性"],
            "guardrails": ["必填校验"],
        },
        "QualityAssuranceCrew": {
            "coverage_focus": ["项目 API", "运行 API"],
            "core_scenarios": [
                {
                    "title": "创建项目并启动运行",
                    "category": "happy_path",
                    "expected_result": "运行完成并产生产物",
                }
            ],
            "acceptance_criteria": ["接口可创建运行"],
            "risk_checklist": ["真实模型超时"],
        },
        "ConsistencyReviewCrew": {
            "coherence_score": 92,
            "aligned_areas": ["命名一致", "接口链路贯通"],
            "conflicts": ["导出能力仍需增强"],
            "next_actions": ["补更多自动化测试"],
        },
    }


def test_app_startup_is_read_only_by_default(tmp_path: Path) -> None:
    db_path = tmp_path / "startup-readonly.db"
    client = build_client(
        db_path,
        extra_env={
            "AUTO_CREATE_SCHEMA": "false",
            "BOOTSTRAP_DATA_ON_STARTUP": "false",
        },
    )

    with client:
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    assert not db_path.exists()


def test_auth_and_run_smoke(tmp_path: Path) -> None:
    client = build_client(tmp_path / "smoke.db")

    with client:
        unauthorized = client.get("/api/v1/projects")
        assert unauthorized.status_code == 401

        headers = login_headers(client)

        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "demo@se-agent.studio"

        project_uid = create_project(
            client,
            headers,
            name="Smoke Project",
            latest_requirement="需要一个可以创建项目、启动运行并查看产物的工作台系统。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要一个可以创建项目、启动运行并查看产物的工作台系统。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)
        artifacts = client.get(f"/api/v1/projects/{project_uid}/artifacts", headers=headers)

        assert tasks.status_code == 200
        assert events.status_code == 200
        assert artifacts.status_code == 200
        assert len(tasks.json()) == 7
        assert len(artifacts.json()) == 7


def test_run_rejects_unknown_or_disabled_workflow(tmp_path: Path) -> None:
    client = build_client(tmp_path / "workflow-validation.db")

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Workflow Validation Project",
            latest_requirement="需要校验 workflow 缺失和停用时的运行创建行为。",
        )

        unknown = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要校验 workflow 缺失时是否返回明确错误。",
                "workflow_code": "missing-workflow",
            },
        )
        assert unknown.status_code == 404
        assert "missing-workflow" in unknown.json()["detail"]

        disable = client.patch(
            "/api/v1/admin/workflows/technical_design_v1",
            headers=headers,
            json={"enabled": False},
        )
        assert disable.status_code == 200
        assert disable.json()["enabled"] is False

        disabled = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要校验 workflow 停用时是否阻止运行。",
                "workflow_code": "technical_design_v1",
            },
        )
        assert disabled.status_code == 409
        assert "disabled" in disabled.json()["detail"]


def test_workflow_steps_drive_run_execution(tmp_path: Path) -> None:
    client = build_client(tmp_path / "workflow-steps.db")

    with client:
        headers = login_headers(client)

        workflow_update = client.patch(
            "/api/v1/admin/workflows/technical_design_v1",
            headers=headers,
            json={
                "steps": [
                    {
                        "step_code": "requirements",
                        "step_type": "crew",
                        "agent_code": "software_architect",
                        "depends_on": [],
                        "parallel_group": None,
                        "output_schema": "RequirementSpec",
                        "sort_order": 10,
                    },
                    {
                        "step_code": "backend_design",
                        "step_type": "crew",
                        "agent_code": "api_tester",
                        "depends_on": ["requirements"],
                        "parallel_group": None,
                        "output_schema": "BackendDesign",
                        "sort_order": 20,
                    },
                ]
            },
        )
        assert workflow_update.status_code == 200
        assert [step["step_code"] for step in workflow_update.json()["steps"]] == ["requirements", "backend_design"]

        project_uid = create_project(
            client,
            headers,
            name="Workflow Driven Project",
            latest_requirement="需要验证 workflow steps 的顺序和 agent 配置会真实驱动执行。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要验证 workflow steps 的顺序和 agent 配置会真实驱动执行。",
                "workflow_code": "technical_design_v1",
            },
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        artifacts = client.get(f"/api/v1/projects/{project_uid}/artifacts", headers=headers)
        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)

        assert tasks.status_code == 200
        assert artifacts.status_code == 200
        assert current.status_code == 200

        task_payload = tasks.json()
        assert [item["step_code"] for item in task_payload] == ["requirements", "backend_design"]
        assert [item["agent_code"] for item in task_payload] == ["software_architect", "api_tester"]
        assert len(artifacts.json()) == 2
        assert current.json()["state_json"]["workflow_code"] == "technical_design_v1"


def test_celery_execution_mode_dispatches_run_to_worker(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "celery-dispatch.db",
        extra_env={"EXECUTION_MODE": "celery"},
    )

    from app.workers.tasks import run_technical_design_flow

    captured: dict[str, object] = {}

    def fake_apply_async(*, args=None, kwargs=None, queue=None, retry=None, retry_policy=None):  # type: ignore[no-untyped-def]
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["queue"] = queue
        captured["retry"] = retry
        captured["retry_policy"] = retry_policy
        return None

    monkeypatch.setattr(run_technical_design_flow, "apply_async", fake_apply_async)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Celery Dispatch Project",
            latest_requirement="需要验证 celery 模式下 run 会被投递给 worker。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要验证 celery 模式下 run 会被投递给 worker。",
                "workflow_code": "technical_design_v1",
            },
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        assert current.status_code == 200
        assert current.json()["status"] == "QUEUED"

        assert captured["args"] == (run_uid,)
        assert captured["queue"] == "flow_runs"
        assert captured["retry"] is True
        assert isinstance(captured["retry_policy"], dict)


def test_celery_dispatch_failure_returns_503(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "celery-dispatch-failure.db",
        extra_env={"EXECUTION_MODE": "celery"},
    )

    from kombu.exceptions import OperationalError

    from app.workers.tasks import run_technical_design_flow

    def fake_apply_async(*, args=None, kwargs=None, queue=None, retry=None, retry_policy=None):  # type: ignore[no-untyped-def]
        raise OperationalError("redis unavailable")

    monkeypatch.setattr(run_technical_design_flow, "apply_async", fake_apply_async)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Celery Failure Project",
            latest_requirement="需要验证 worker 不可用时创建运行会返回 503。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要验证 worker 不可用时创建运行会返回 503。",
                "workflow_code": "technical_design_v1",
            },
        )
        assert run.status_code == 503
        assert "Celery Worker" in run.json()["detail"]


def test_user_llm_config_crud(tmp_path: Path) -> None:
    client = build_client(tmp_path / "llm-config.db")

    with client:
        headers = login_headers(client)

        initial = client.get("/api/v1/llm-config", headers=headers)
        assert initial.status_code == 200
        assert initial.json()["has_api_key"] is False
        assert initial.json()["is_ready"] is False

        update = client.put(
            "/api/v1/llm-config",
            headers=headers,
            json={
                "provider_name": "OpenAI Compatible",
                "base_url": "https://api.example.com/v1",
                "default_model": "gpt-4.1-mini",
                "api_key": "sk-test-user-config-1234",
                "enabled": True,
            },
        )
        assert update.status_code == 200
        assert update.json()["has_api_key"] is True
        assert update.json()["masked_api_key"].startswith("sk-t")
        assert update.json()["masked_api_key"].endswith("1234")
        assert update.json()["is_ready"] is True

        fetched = client.get("/api/v1/llm-config", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["base_url"] == "https://api.example.com/v1"
        assert fetched.json()["enabled"] is True
        assert fetched.json()["has_api_key"] is True

        cleared = client.put(
            "/api/v1/llm-config",
            headers=headers,
            json={
                "clear_api_key": True,
                "enabled": False,
            },
        )
        assert cleared.status_code == 200
        assert cleared.json()["has_api_key"] is False
        assert cleared.json()["masked_api_key"] == ""
        assert cleared.json()["is_ready"] is False


def test_user_llm_config_enables_crewai_auto_mode(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "llm-config-auto.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "auto",
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    payloads = build_crewai_payloads()
    captured_runtime: dict[str, str] = {}

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        captured_runtime["base_url"] = self.runtime_config.base_url if self.runtime_config else ""
        captured_runtime["api_key"] = self.runtime_config.api_key if self.runtime_config else ""
        captured_runtime["agent_model"] = agent_profile.model
        captured_runtime["resolved_model"] = self.resolve_model_name(agent_profile)
        return CrewAIStageRunResult(
            payload=payloads[crew_name],
            raw_output="{}",
            prompt_tokens=64,
            completion_tokens=96,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        configured = client.put(
            "/api/v1/llm-config",
            headers=headers,
            json={
                "provider_name": "Moonshot Compatible",
                "base_url": "https://llm.example.com/v1",
                "default_model": "moonshot-v1-8k",
                "api_key": "sk-user-runtime-5678",
                "enabled": True,
            },
        )
        assert configured.status_code == 200
        assert configured.json()["is_ready"] is True

        project_uid = create_project(
            client,
            headers,
            name="User Runtime Config Project",
            latest_requirement="需要验证用户配置的云端 API 会驱动真实智能体运行。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要验证用户配置的云端 API 会驱动真实智能体运行。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)
        assert events.status_code == 200
        assert captured_runtime["base_url"] == "https://llm.example.com/v1"
        assert captured_runtime["api_key"] == "sk-user-runtime-5678"
        assert captured_runtime["agent_model"] == "gpt-4.1-mini"
        assert captured_runtime["resolved_model"] == "moonshot-v1-8k"
        assert any(
            event["payload_json"].get("runtime_mode") == "crewai"
            for event in events.json()
            if event["event_type"].startswith("task.")
        )

    import json
    import sqlite3

    with sqlite3.connect(tmp_path / "llm-config-auto.db") as connection:
        prompt_snapshot_text = connection.execute(
            "select prompt_snapshot from task_runs order by id desc limit 1"
        ).fetchone()[0]

    prompt_snapshot = json.loads(prompt_snapshot_text)
    assert prompt_snapshot["runtime"]["model"] == "moonshot-v1-8k"


def test_cancel_run_preserves_cancelled_status_during_inflight_stage(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "cancel-inflight.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunner

    started = Event()
    release = Event()

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        started.set()
        release.wait(2)
        raise RuntimeError("synthetic stage failure after cancel")

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Cancelable Run Project",
            latest_requirement="需要验证运行中点击取消时，最终状态会保留为已取消。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要验证运行中点击取消时，最终状态会保留为已取消。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        assert started.wait(2) is True

        cancelled = client.post(f"/api/v1/runs/{run_uid}/cancel", headers=headers)
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        release.set()

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "CANCELLED"

        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)

        assert tasks.status_code == 200
        assert events.status_code == 200
        assert tasks.json()[-1]["status"] == "CANCELLED"
        event_types = [item["event_type"] for item in events.json()]
        assert "flow.cancel_requested" in event_types
        assert "task.cancelled" in event_types
        assert "flow.cancelled" in event_types


def test_crewai_runner_retries_without_structured_output(monkeypatch) -> None:
    from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
    from app.orchestrators.outputs.requirement_models import RequirementsStageOutput
    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner
    from app.services.llm_config_service import RuntimeLLMConfig

    runner = CrewAIStageRunner(
        runtime_config=RuntimeLLMConfig(
            provider_name="Moonshot Compatible",
            base_url="https://llm.example.com/v1",
            api_key="sk-test",
            default_model="moonshot-v1-8k",
        )
    )
    payload = build_crewai_payloads()["RequirementAnalysisCrew"]
    attempts: list[bool] = []

    def fake_kickoff_stage(self, *, use_structured_output, **kwargs):  # type: ignore[no-untyped-def]
        attempts.append(use_structured_output)
        if use_structured_output:
            raise RuntimeError("This response_format type is unavailable now")
        return CrewAIStageRunResult(
            payload=payload,
            raw_output=json.dumps(payload, ensure_ascii=False),
            prompt_tokens=12,
            completion_tokens=24,
        )

    monkeypatch.setattr(CrewAIStageRunner, "_kickoff_stage", fake_kickoff_stage)

    result = runner.run_stage(
        crew_name="RequirementAnalysisCrew",
        agent_profile=ResolvedAgentProfile(
            agent_code="product_manager",
            display_name="Product Manager",
            description="",
            model="gpt-4.1-mini",
            temperature=0.2,
            allow_delegation=False,
            prompt_snapshot={},
        ),
        task_description="请输出结构化需求。",
        expected_output="Return a RequirementsStageOutput.",
        output_model=RequirementsStageOutput,
    )

    assert attempts == [True, False]
    assert result.payload["requirement_spec"]["project_name"] == "SE-Agent Studio"


def test_crewai_runner_skips_structured_output_for_deepseek(monkeypatch) -> None:
    from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
    from app.orchestrators.outputs.requirement_models import RequirementsStageOutput
    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner
    from app.services.llm_config_service import RuntimeLLMConfig

    runner = CrewAIStageRunner(
        runtime_config=RuntimeLLMConfig(
            provider_name="DeepSeek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test",
            default_model="deepseek-chat",
        )
    )
    payload = build_crewai_payloads()["RequirementAnalysisCrew"]
    attempts: list[bool] = []

    def fake_kickoff_stage(self, *, use_structured_output, **kwargs):  # type: ignore[no-untyped-def]
        attempts.append(use_structured_output)
        return CrewAIStageRunResult(
            payload=payload,
            raw_output=json.dumps(payload, ensure_ascii=False),
            prompt_tokens=12,
            completion_tokens=24,
        )

    monkeypatch.setattr(CrewAIStageRunner, "_kickoff_stage", fake_kickoff_stage)

    result = runner.run_stage(
        crew_name="RequirementAnalysisCrew",
        agent_profile=ResolvedAgentProfile(
            agent_code="product_manager",
            display_name="Product Manager",
            description="",
            model="gpt-4.1-mini",
            temperature=0.2,
            allow_delegation=False,
            prompt_snapshot={},
        ),
        task_description="请输出结构化需求。",
        expected_output="Return a RequirementsStageOutput.",
        output_model=RequirementsStageOutput,
    )

    assert attempts == [False]
    assert result.payload["requirement_spec"]["project_name"] == "SE-Agent Studio"


def test_crewai_backstory_does_not_repeat_project_context() -> None:
    from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
    from app.orchestrators.runtime import CrewAIStageRunner

    runner = CrewAIStageRunner()
    profile = ResolvedAgentProfile(
        agent_code="product_manager",
        display_name="Product Manager",
        description="负责把需求整理成结构化设计输入。",
        model="gpt-4.1-mini",
        temperature=0.2,
        allow_delegation=False,
        prompt_snapshot={
            "system_rules": ["必须输出结构化内容"],
            "backstory": "你熟悉软件工程项目需求拆解。",
            "rules": "禁止输出占位符。",
            "context": {"project_name": "SE-Agent Studio", "modules": ["API", "UI"]},
        },
    )

    composed = runner._compose_backstory(profile)

    assert "Project Context" not in composed
    assert "SE-Agent Studio" not in composed
    assert "必须输出结构化内容" in composed
    assert "禁止输出占位符" in composed


def test_flow_later_stage_context_is_compact() -> None:
    from app.orchestrators.flows.technical_design_flow import TechnicalDesignFlow
    from app.orchestrators.outputs.flow_models import ProjectFlowState

    payloads = build_crewai_payloads()
    flow = object.__new__(TechnicalDesignFlow)
    flow.state = ProjectFlowState(
        project_id=1,
        flow_run_uid="run-compact-context",
        workflow_code="technical_design_v1",
        requirement_text="需要一个支持项目管理、运行监控、产物中心和模型配置的多智能体软件工程工作台。",
        requirement_spec=payloads["RequirementAnalysisCrew"]["requirement_spec"],
        task_breakdown=payloads["RequirementAnalysisCrew"]["task_breakdown"],
        architecture_blueprint=payloads["ArchitectureDesignCrew"],
        backend_design=payloads["BackendDesignCrew"],
        frontend_blueprint=payloads["FrontendDesignCrew"],
        ai_integration_spec=payloads["AIPlatformDesignCrew"],
        api_test_plan=payloads["QualityAssuranceCrew"],
        current_stage="backend_design",
        artifact_ids=[1, 2, 3],
    )

    full_state = json.dumps(
        flow.state.model_dump(mode="json", exclude={"artifact_ids"}),
        ensure_ascii=False,
    )
    stage = SimpleNamespace(
        step_code="quality_assurance",
        artifact_title="测试与验收方案",
        goal="为当前项目准备测试与验收计划。",
    )

    compact_context = TechnicalDesignFlow._build_stage_context(flow, stage, flow.state)
    description = TechnicalDesignFlow._build_task_description(flow, stage, flow.state)

    assert "requirement_summary" in compact_context
    assert "architecture_summary" in compact_context
    assert "backend_summary" in compact_context
    assert "frontend_summary" in compact_context
    assert "ai_summary" in compact_context
    assert "requirement_text" not in compact_context
    assert "backend_design" not in compact_context
    assert "frontend_blueprint" not in compact_context
    assert "Original project requirement:" not in description
    assert "Project brief summary:" in description
    assert len(json.dumps(compact_context, ensure_ascii=False)) < len(full_state) * 0.5


def test_crewai_runner_extracts_json_from_markdown_block() -> None:
    from app.orchestrators.outputs.requirement_models import RequirementsStageOutput
    from app.orchestrators.runtime import CrewAIStageRunner

    runner = CrewAIStageRunner()
    payload = build_crewai_payloads()["RequirementAnalysisCrew"]
    text = f"```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```"

    parsed = runner._extract_payload_from_text(text, RequirementsStageOutput)

    assert parsed["requirement_spec"]["project_name"] == "SE-Agent Studio"
    assert parsed["task_breakdown"]["priorities"] == ["先打通主链路"]


def test_crewai_runtime_dispatch_smoke(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "crewai.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    payloads = build_crewai_payloads()

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        return CrewAIStageRunResult(
            payload=payloads[crew_name],
            raw_output="{}",
            prompt_tokens=128,
            completion_tokens=256,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="CrewAI Runtime Project",
            latest_requirement="需要一个能真实调用多智能体运行时的课程项目工作台。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要一个能真实调用多智能体运行时的课程项目工作台。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)
        artifacts = client.get(f"/api/v1/projects/{project_uid}/artifacts", headers=headers)

        assert events.status_code == 200
        assert artifacts.status_code == 200
        assert len(artifacts.json()) == 7
        assert any(
            event["payload_json"].get("runtime_mode") == "crewai"
            for event in events.json()
            if event["event_type"].startswith("task.")
        )


def test_parallel_group_stages_run_concurrently(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "parallel-group.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner
    from app.services.run_service import RunService, execute_run_in_session

    payloads = build_crewai_payloads()
    design_crews = {"BackendDesignCrew", "FrontendDesignCrew", "AIPlatformDesignCrew"}

    def fake_dispatch_run(self, run_uid: str) -> None:
        execute_run_in_session(run_uid, raise_on_failure=True)

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        if crew_name in design_crews:
            time.sleep(0.25)
        return CrewAIStageRunResult(
            payload=payloads[crew_name],
            raw_output="{}",
            prompt_tokens=32,
            completion_tokens=48,
        )

    monkeypatch.setattr(RunService, "dispatch_run", fake_dispatch_run)
    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Parallel Design Project",
            latest_requirement="需要验证 design 并行组会同时执行 backend、frontend 和 ai 三个阶段。",
        )

        started = time.perf_counter()
        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要验证 design 并行组会同时执行 backend、frontend 和 ai 三个阶段。"},
        )
        elapsed = time.perf_counter() - started

        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)

        assert current.status_code == 200
        assert current.json()["status"] == "COMPLETED"
        assert tasks.status_code == 200
        assert elapsed < 0.6

        design_tasks = [
            item
            for item in tasks.json()
            if item["step_code"] in {"backend_design", "frontend_design", "ai_design"}
        ]
        assert len(design_tasks) == 3

        started_at = [datetime.fromisoformat(item["started_at"]) for item in design_tasks]
        assert (max(started_at) - min(started_at)).total_seconds() < 0.1
