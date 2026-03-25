from __future__ import annotations

import importlib
import os
import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient


def build_client(db_path: Path, extra_env: dict[str, str] | None = None) -> TestClient:
    defaults = {
        "DATABASE_URL": f"sqlite:///{db_path}",
        "AUTO_CREATE_SCHEMA": "true",
        "DEFAULT_OWNER_PASSWORD": "ChangeMe123!",
        "JWT_SECRET": "0123456789abcdef0123456789abcdef",
        "OPENAI_API_KEY": "",
        "OPENAI_BASE_URL": "https://api.openai.com/v1",
        "AGENT_RUNTIME_MODE": "template",
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


def test_auth_and_run_smoke(tmp_path: Path) -> None:
    client = build_client(tmp_path / "smoke.db")

    with client:
        unauthorized = client.get("/api/v1/projects")
        assert unauthorized.status_code == 401

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "demo@se-agent.studio", "password": "ChangeMe123!"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "demo@se-agent.studio"

        project = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "Smoke Project",
                "description": "自动化测试项目",
                "latest_requirement": "需要一个可以创建项目、启动运行并查看产物的工作台系统。",
            },
        )
        assert project.status_code == 201
        project_uid = project.json()["uid"]

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要一个可以创建项目、启动运行并查看产物的工作台系统。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = None
        for _ in range(30):
            current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
            assert current.status_code == 200
            final_status = current.json()["status"]
            if final_status in {"COMPLETED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.2)

        assert final_status == "COMPLETED"

        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)
        artifacts = client.get(f"/api/v1/projects/{project_uid}/artifacts", headers=headers)

        assert tasks.status_code == 200
        assert events.status_code == 200
        assert artifacts.status_code == 200
        assert len(tasks.json()) == 7
        assert len(artifacts.json()) == 7


def test_crewai_runtime_dispatch_smoke(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "crewai.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    payloads = {
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

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        return CrewAIStageRunResult(
            payload=payloads[crew_name],
            raw_output="{}",
            prompt_tokens=128,
            completion_tokens=256,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": "demo@se-agent.studio", "password": "ChangeMe123!"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        project = client.post(
            "/api/v1/projects",
            headers=headers,
            json={
                "name": "CrewAI Runtime Project",
                "description": "CrewAI 运行时测试项目",
                "latest_requirement": "需要一个能真实调用多智能体运行时的课程项目工作台。",
            },
        )
        assert project.status_code == 201
        project_uid = project.json()["uid"]

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要一个能真实调用多智能体运行时的课程项目工作台。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = None
        for _ in range(30):
            current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
            assert current.status_code == 200
            final_status = current.json()["status"]
            if final_status in {"COMPLETED", "FAILED", "CANCELLED"}:
                break
            time.sleep(0.2)

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
