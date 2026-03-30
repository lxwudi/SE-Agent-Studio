from __future__ import annotations

import importlib
import io
import json
import os
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from threading import Event
from textwrap import dedent
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
                "problem_statement": "需要一个多智能体软件工程工作台，用于把需求整理为结构化设计文档并追踪整个执行流程。",
                "target_users": ["学生", "教师", "管理员"],
                "core_features": [
                    "创建项目并维护最新需求",
                    "启动多阶段运行并查看执行状态",
                    "统一查看结构化产物和 Markdown 文档",
                ],
                "non_functional_requirements": ["结构化输出", "可追踪", "便于课程项目演示"],
                "constraints": ["固定流程", "FastAPI + Vue", "优先兼容 OpenAI 风格接口"],
                "assumptions": ["单租户课程场景", "由管理员维护工作流和智能体模板"],
                "open_questions": ["是否启用人工审核", "是否提供产物导出能力"],
            },
            "task_breakdown": {
                "milestones": [
                    {
                        "title": "需求结构化",
                        "owner_role": "Product Manager",
                        "objective": "将自然语言需求整理为规范化 RequirementSpec",
                        "deliverable": "RequirementSpec",
                    },
                    {
                        "title": "技术方案设计",
                        "owner_role": "Software Architect",
                        "objective": "形成架构、前端、后端与 AI 集成的协同设计方案",
                        "deliverable": "ArchitectureBlueprint + Design Specs",
                    },
                ],
                "priorities": ["先打通主链路", "保证阶段产物可审阅", "补齐运行观测能力"],
                "clarification_list": ["明确部署环境", "明确模型提供方", "明确是否需要人工审核"],
            },
        },
        "ArchitectureDesignCrew": {
            "architecture_style": "模块化单体 + 异步 Worker",
            "core_modules": ["API", "Flow", "Worker", "Frontend"],
            "data_flow": ["用户提交需求 -> 生成运行记录", "阶段执行后落库产物并推送事件"],
            "deployment_units": ["web-api", "worker", "mysql", "redis", "frontend"],
            "key_decisions": ["Flow 管总控", "Schema First"],
            "risks": ["模型成本", "运行失败时的恢复语义仍需加强"],
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
                },
                {
                    "name": "artifact",
                    "purpose": "持久化每个阶段的结构化产物和 Markdown 文档",
                    "key_fields": ["artifact_uid", "artifact_type", "content_markdown"],
                }
            ],
            "api_contracts": [
                {
                    "method": "POST",
                    "path": "/api/v1/projects/{project_uid}/runs",
                    "summary": "创建运行",
                    "request_shape": "RunCreate",
                    "response_shape": "FlowRunDetail",
                },
                {
                    "method": "GET",
                    "path": "/api/v1/runs/{run_uid}",
                    "summary": "查询运行状态",
                    "request_shape": "None",
                    "response_shape": "FlowRunDetail",
                }
            ],
            "async_strategy": ["Celery + Redis", "开发环境允许 thread mode"],
            "observability": ["run_event", "task_run"],
            "risks": ["需要更多权限隔离"],
        },
        "FrontendDesignCrew": {
            "page_tree": [
                {
                    "page_name": "项目列表",
                    "goal": "查看和创建项目",
                    "key_sections": ["项目卡片", "最近活动"],
                },
                {
                    "page_name": "运行监控",
                    "goal": "查看当前阶段、事件流与产物摘要",
                    "key_sections": ["阶段轨道", "事件列表", "产物预览"],
                }
            ],
            "component_map": ["ShellLayout", "ArtifactPanel", "RunStageRail"],
            "state_slices": ["authStore", "runStore"],
            "api_bindings": ["GET /api/v1/projects", "GET /api/v1/runs/{run_uid}"],
            "realtime_strategy": ["优先 SSE"],
        },
        "AIPlatformDesignCrew": {
            "provider_strategy": ["OpenAI 兼容接口", "允许按用户配置覆盖默认模型"],
            "model_policy": ["按 agent_profile 选择模型"],
            "prompt_policy": ["运行时固化 prompt 快照", "记录每个阶段的上下文与输出 schema"],
            "output_schemas": ["RequirementSpec", "ArchitectureBlueprint"],
            "evaluation_plan": ["校验字段完整性"],
            "guardrails": ["必填校验", "禁止占位式输出"],
        },
        "QualityAssuranceCrew": {
            "coverage_focus": ["项目 API", "运行 API"],
            "core_scenarios": [
                {
                    "title": "创建项目并启动运行",
                    "category": "happy_path",
                    "expected_result": "运行完成并产生产物",
                },
                {
                    "title": "运行失败时记录错误事件",
                    "category": "failure_path",
                    "expected_result": "flow.failed 事件被持久化并可在前端查看",
                }
            ],
            "acceptance_criteria": ["接口可创建运行", "运行结束后可查询到阶段产物"],
            "risk_checklist": ["真实模型超时"],
        },
        "ConsistencyReviewCrew": {
            "coherence_score": 92,
            "aligned_areas": [
                "命名一致，阶段产物与接口字段保持统一",
                "接口链路贯通，项目、运行、产物查询路径能够形成闭环",
            ],
            "conflicts": [
                "导出能力仍需增强，当前更适合在系统内查看 Markdown 结果",
            ],
            "next_actions": [
                "补更多自动化测试，并覆盖真实运行时接入后的失败恢复场景",
            ],
        },
    }


def build_delivery_crewai_payloads(*, broken_backend: bool = False) -> dict[str, dict]:
    backend_main_content = (
        dedent(
            """
            from fastapi import FastAPI


            app = FastAPI(title="Broken Delivery API")
            """
        ).strip()
        + "\n"
        if broken_backend
        else dedent(
            """
            from typing import List

            from fastapi import FastAPI, HTTPException, Response, status
            from fastapi.middleware.cors import CORSMiddleware
            from pydantic import BaseModel, Field


            app = FastAPI(title="Delivery Repair API")

            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
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
                Task(id=1, title="整理需求", done=True),
                Task(id=2, title="生成代码", done=False),
            ]
            NEXT_ID = 3


            @app.get("/healthz")
            def healthz() -> dict[str, str]:
                return {"status": "ok"}


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


            @app.put("/api/tasks/{task_id}", response_model=Task)
            def update_task(task_id: int, payload: TaskUpdate) -> Task:
                for index, task in enumerate(TASKS):
                    if task.id == task_id:
                        updated = Task(id=task_id, **payload.model_dump())
                        TASKS[index] = updated
                        return updated
                raise HTTPException(status_code=404, detail="Task not found")


            @app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
            def delete_task(task_id: int) -> Response:
                for index, task in enumerate(TASKS):
                    if task.id == task_id:
                        TASKS.pop(index)
                        return Response(status_code=status.HTTP_204_NO_CONTENT)
                raise HTTPException(status_code=404, detail="Task not found")
            """
        ).strip()
        + "\n"
    )

    backend_bundle = {
        "bundle_name": "Backend Delivery Bundle",
        "summary": "交付一个可本地运行的 FastAPI 任务管理 API，并附带 smoke test。",
        "runtime": "python",
        "entrypoints": ["backend/main.py", "backend/test_api.py"],
        "files": [
            {
                "path": "backend/requirements.txt",
                "language": "text",
                "purpose": "后端运行依赖",
                "content": "fastapi==0.115.0\nuvicorn[standard]==0.32.0\npydantic==2.9.2\n",
            },
            {
                "path": "backend/requirements-dev.txt",
                "language": "text",
                "purpose": "后端测试依赖",
                "content": "-r requirements.txt\npytest==8.3.3\nhttpx==0.28.1\n",
            },
            {
                "path": "backend/main.py",
                "language": "python",
                "purpose": "FastAPI 应用入口和任务 CRUD API",
                "content": backend_main_content,
            },
            {
                "path": "backend/test_api.py",
                "language": "python",
                "purpose": "后端最小 smoke test",
                "content": dedent(
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
                ).strip()
                + "\n",
            },
        ],
        "run_commands": [
            {
                "label": "启动后端服务",
                "command": "cd backend && uvicorn main:app --reload --port 8001",
                "purpose": "本地启动 API 服务",
            }
        ],
        "setup_notes": [
            "后端默认监听 http://127.0.0.1:8001",
            "当前数据以内存方式保存，适合本地演示。",
        ],
    }

    frontend_bundle = {
        "bundle_name": "Frontend Delivery Bundle",
        "summary": "交付一个可直接静态托管的任务面板页面，并默认联调本地后端。",
        "runtime": "browser",
        "entrypoints": ["frontend/index.html", "frontend/app.js"],
        "files": [
            {
                "path": "frontend/index.html",
                "language": "html",
                "purpose": "页面入口与结构骨架",
                "content": dedent(
                    """
                    <!doctype html>
                    <html lang="zh-CN">
                      <head>
                        <meta charset="UTF-8" />
                        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                        <title>Delivery Repair UI</title>
                        <link rel="stylesheet" href="./styles.css" />
                      </head>
                      <body>
                        <main>
                          <form id="taskForm">
                            <input id="taskInput" type="text" />
                            <button type="submit">新增任务</button>
                          </form>
                          <ul id="taskList"></ul>
                        </main>
                        <template id="taskItemTemplate">
                          <li><input type="checkbox" /><span class="task-title"></span><button class="task-delete">删除</button></li>
                        </template>
                        <script src="./app.js" type="module"></script>
                      </body>
                    </html>
                    """
                ).strip()
                + "\n",
            },
            {
                "path": "frontend/app.js",
                "language": "javascript",
                "purpose": "任务列表渲染与 API 调用逻辑",
                "content": dedent(
                    """
                    const API_BASE = "http://127.0.0.1:8001";
                    const TASKS_PATH = "/api/tasks";

                    async function loadTasks() {
                      const response = await fetch(`${API_BASE}${TASKS_PATH}`);
                      return response.json();
                    }

                    document.getElementById("taskForm").addEventListener("submit", async (event) => {
                      event.preventDefault();
                      await fetch(`${API_BASE}${TASKS_PATH}`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ title: "新增任务", done: false }),
                      });
                      await loadTasks();
                    });
                    """
                ).strip()
                + "\n",
            },
            {
                "path": "frontend/styles.css",
                "language": "css",
                "purpose": "前端页面样式",
                "content": "body { font-family: sans-serif; }\n",
            },
        ],
        "run_commands": [
            {
                "label": "启动前端页面",
                "command": "cd frontend && python3 -m http.server 4173",
                "purpose": "本地打开静态页面",
            }
        ],
        "setup_notes": [
            "前端默认请求 http://127.0.0.1:8001",
            "可以替换 API_BASE 适配其他环境。",
        ],
    }

    return {
        "RequirementAnalysisCrew": {
            "app_name": "交付修复工作台",
            "app_summary": "需要一个可以交付前后端 starter 代码，并在验证失败时自动修复的项目工作台。",
            "target_users": ["产品经理", "研发同学", "验收人员"],
            "core_capabilities": ["生成后端 starter", "生成前端 starter", "自动验证并尝试修复"],
            "acceptance_criteria": ["后端测试可通过", "前端契约检查可通过", "产物中包含最终代码"],
            "non_goals": ["暂不处理数据库持久化"],
        },
        "ArchitectureDesignCrew": {
            "architecture_style": "FastAPI + 静态页面 + 自动验证修复闭环",
            "stack_choices": ["FastAPI", "原生 HTML/CSS/JS", "pytest", "本地工作区交付"],
            "workspace_layout": [
                "README.md",
                "backend/main.py",
                "backend/test_api.py",
                "frontend/index.html",
                "frontend/app.js",
                "frontend/styles.css",
            ],
            "implementation_order": ["生成需求规格", "生成前后端代码包", "集成验证并自动修复"],
            "run_commands": [
                {"label": "启动后端", "command": "uvicorn main:app --reload --port 8001", "purpose": "运行 API"},
                {"label": "启动前端", "command": "python3 -m http.server 4173", "purpose": "打开页面"},
            ],
            "validation_commands": [
                {"label": "pytest", "command": "pytest test_api.py", "purpose": "验证后端 CRUD"},
            ],
            "delivery_notes": ["优先保证 starter 可运行", "验证失败时应触发自动修复"],
        },
        "BackendDesignCrew": backend_bundle,
        "FrontendDesignCrew": frontend_bundle,
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
        artifact_detail = client.get(f"/api/v1/artifacts/{artifacts.json()[0]['artifact_uid']}", headers=headers)

        assert tasks.status_code == 200
        assert events.status_code == 200
        assert artifacts.status_code == 200
        assert artifact_detail.status_code == 200
        assert len(tasks.json()) == 7
        assert len(artifacts.json()) == 7
        assert "## 文档元信息" in artifact_detail.json()["content_markdown"]
        assert "## 质量检查" in artifact_detail.json()["content_markdown"]
        assert "⚠️ 当前文档由显式 template 草稿模式生成" in artifact_detail.json()["content_markdown"]


def test_project_can_be_deleted(tmp_path: Path) -> None:
    client = build_client(tmp_path / "project-delete.db")

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Delete Me",
            latest_requirement="验证删除项目接口是否可用。",
        )

        before = client.get("/api/v1/projects", headers=headers)
        assert before.status_code == 200
        assert any(item["uid"] == project_uid for item in before.json())

        deleted = client.delete(f"/api/v1/projects/{project_uid}", headers=headers)
        assert deleted.status_code == 204

        detail = client.get(f"/api/v1/projects/{project_uid}", headers=headers)
        after = client.get("/api/v1/projects", headers=headers)

        assert detail.status_code == 404
        assert after.status_code == 200
        assert all(item["uid"] != project_uid for item in after.json())


def test_project_delivery_package_downloads_zip(tmp_path: Path) -> None:
    client = build_client(tmp_path / "project-package.db")

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Package Project",
            latest_requirement="需要生成一个可下载的项目压缩包。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要生成一个可下载的项目压缩包。",
                "workflow_code": "delivery_v1",
            },
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        package = client.get(f"/api/v1/projects/{project_uid}/package", headers=headers)
        assert package.status_code == 200
        assert package.headers["content-type"] == "application/zip"
        assert "attachment; filename=" in package.headers["content-disposition"]

        archive = zipfile.ZipFile(io.BytesIO(package.content))
        names = archive.namelist()
        assert any(name.endswith("/backend/main.py") for name in names)
        assert any(name.endswith("/frontend/index.html") for name in names)
        assert any(name.endswith("/README.md") for name in names)


def test_delivery_workflow_generates_runnable_workspace(tmp_path: Path) -> None:
    client = build_client(tmp_path / "delivery-smoke.db")

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Delivery Project",
            latest_requirement="需要一个能交付前后端 starter 代码并给出启动步骤的软件工程项目工作台。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要一个能交付前后端 starter 代码并给出启动步骤的软件工程项目工作台。",
                "workflow_code": "delivery_v1",
            },
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        artifacts = client.get(f"/api/v1/projects/{project_uid}/artifacts", headers=headers)

        assert current.status_code == 200
        assert tasks.status_code == 200
        assert artifacts.status_code == 200
        assert current.json()["workflow_code"] == "delivery_v1"
        assert [item["step_code"] for item in tasks.json()] == [
            "delivery_requirements",
            "solution_design",
            "backend_delivery",
            "frontend_delivery",
            "integration",
            "handoff",
        ]
        assert len(artifacts.json()) == 6

        workspace_root = Path(current.json()["state_json"]["delivery_handoff"]["workspace_root"])
        integration_bundle = current.json()["state_json"]["integration_bundle"]
        handoff_bundle = current.json()["state_json"]["delivery_handoff"]

        assert workspace_root.exists()
        assert (workspace_root / "README.md").exists()
        assert (workspace_root / "backend" / "main.py").exists()
        assert (workspace_root / "backend" / "test_api.py").exists()
        assert (workspace_root / "frontend" / "index.html").exists()
        assert (workspace_root / "frontend" / "app.js").exists()
        assert len(integration_bundle["files"]) >= 6
        assert len(integration_bundle["verification_results"]) == 2
        assert all(item["success"] is True for item in integration_bundle["verification_results"])
        assert len(handoff_bundle["verification_results"]) == 2
        assert any("自动验证已执行 2 项" in item for item in handoff_bundle["verification_status"])


def test_delivery_crewai_repairs_failed_backend_verification(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "delivery-crewai-repair.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    broken_payloads = build_delivery_crewai_payloads(broken_backend=True)
    fixed_payloads = build_delivery_crewai_payloads(broken_backend=False)
    backend_calls = 0

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        nonlocal backend_calls
        if crew_name == "BackendDesignCrew":
            backend_calls += 1
            payload = broken_payloads[crew_name] if backend_calls == 1 else fixed_payloads[crew_name]
        elif crew_name in fixed_payloads:
            payload = fixed_payloads[crew_name]
        else:
            raise AssertionError(f"Unexpected crew name for delivery workflow: {crew_name}")
        return CrewAIStageRunResult(
            payload=payload,
            raw_output="{}",
            prompt_tokens=72,
            completion_tokens=120,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Delivery Repair Project",
            latest_requirement="需要验证交付流在后端测试失败时会自动修复并给出最终可运行代码。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要验证交付流在后端测试失败时会自动修复并给出最终可运行代码。",
                "workflow_code": "delivery_v1",
            },
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"
        assert backend_calls == 2

        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)

        assert current.status_code == 200
        assert events.status_code == 200

        integration_bundle = current.json()["state_json"]["integration_bundle"]
        handoff_bundle = current.json()["state_json"]["delivery_handoff"]
        final_files = {item["path"]: item["content"] for item in integration_bundle["files"]}

        assert all(item["success"] is True for item in integration_bundle["verification_results"])
        assert any("第 1 轮自动修复已执行" in item for item in integration_bundle["notes"])
        assert any("自动验证已执行 2 项，当前通过 2 项。" in item for item in handoff_bundle["verification_status"])
        assert "/healthz" in final_files["backend/main.py"]
        assert any(event["event_type"] == "delivery.verification.completed" for event in events.json())
        assert any(event["event_type"] == "delivery.repair.started" for event in events.json())
        assert any(event["event_type"] == "delivery.repair.completed" for event in events.json())


def test_delivery_crewai_falls_back_to_template_when_codebundle_json_is_truncated(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "delivery-crewai-fallback.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    payloads = build_delivery_crewai_payloads(broken_backend=False)

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        if crew_name in {"BackendDesignCrew", "FrontendDesignCrew"}:
            raise ValueError(
                "1 validation error for CodeBundle\n"
                "  Invalid JSON: EOF while parsing a string at line 12 column 999 [type=json_invalid, input_value='{\"bundle_name\": \"截断\"', input_type=str]"
            )
        if crew_name not in payloads:
            raise AssertionError(f"Unexpected crew name for delivery workflow fallback test: {crew_name}")
        return CrewAIStageRunResult(
            payload=payloads[crew_name],
            raw_output="{}",
            prompt_tokens=48,
            completion_tokens=80,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Delivery Fallback Project",
            latest_requirement="需要验证当云端模型返回截断 JSON 时，交付流会自动回退到稳定 starter 模板。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={
                "requirement_text": "需要验证当云端模型返回截断 JSON 时，交付流会自动回退到稳定 starter 模板。",
                "workflow_code": "delivery_v1",
            },
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "COMPLETED"

        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)

        assert current.status_code == 200
        assert events.status_code == 200

        integration_bundle = current.json()["state_json"]["integration_bundle"]
        backend_bundle = current.json()["state_json"]["backend_code_bundle"]
        frontend_bundle = current.json()["state_json"]["frontend_code_bundle"]

        assert all(item["success"] is True for item in integration_bundle["verification_results"])
        assert any("自动回退到稳定 starter 模板" in item for item in backend_bundle["setup_notes"])
        assert any("自动回退到稳定 starter 模板" in item for item in frontend_bundle["setup_notes"])
        assert any(event["event_type"] == "delivery.stage_fallback" for event in events.json())


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
        assert initial.json()["agent_model_overrides"] == {}
        frontend_initial = next(item for item in initial.json()["available_roles"] if item["agent_code"] == "frontend_developer")
        assert frontend_initial["override_enabled"] is False
        assert frontend_initial["has_api_key"] is False

        update = client.put(
            "/api/v1/llm-config",
            headers=headers,
            json={
                "provider_name": "OpenAI Compatible",
                "base_url": "https://api.example.com/v1",
                "default_model": "gpt-4.1-mini",
                "agent_overrides": {
                    "frontend_developer": {
                        "override_enabled": True,
                        "provider_name": "DeepSeek",
                        "base_url": "https://api.deepseek.com/v1",
                        "default_model": "deepseek-chat",
                        "api_key": "sk-role-frontend-1234",
                    },
                    "backend_architect": {
                        "override_enabled": True,
                        "default_model": "gpt-4o-mini",
                    },
                },
                "api_key": "sk-test-user-config-1234",
                "enabled": True,
            },
        )
        assert update.status_code == 200
        assert update.json()["has_api_key"] is True
        assert update.json()["masked_api_key"].startswith("sk-t")
        assert update.json()["masked_api_key"].endswith("1234")
        assert update.json()["is_ready"] is True
        assert update.json()["agent_model_overrides"]["frontend_developer"] == "deepseek-chat"
        assert update.json()["agent_model_overrides"]["backend_architect"] == "gpt-4o-mini"
        frontend_role = next(item for item in update.json()["available_roles"] if item["agent_code"] == "frontend_developer")
        assert frontend_role["override_enabled"] is True
        assert frontend_role["provider_name"] == "DeepSeek"
        assert frontend_role["base_url"] == "https://api.deepseek.com/v1"
        assert frontend_role["default_model"] == "deepseek-chat"
        assert frontend_role["has_api_key"] is True
        assert frontend_role["masked_api_key"].startswith("sk-r")

        fetched = client.get("/api/v1/llm-config", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["base_url"] == "https://api.example.com/v1"
        assert fetched.json()["enabled"] is True
        assert fetched.json()["has_api_key"] is True
        assert fetched.json()["agent_model_overrides"]["frontend_developer"] == "deepseek-chat"

        cleared = client.put(
            "/api/v1/llm-config",
            headers=headers,
            json={
                "clear_api_key": True,
                "agent_overrides": {
                    "frontend_developer": {
                        "override_enabled": False,
                        "provider_name": "",
                        "base_url": "",
                        "default_model": "",
                        "clear_api_key": True,
                    },
                    "backend_architect": {
                        "override_enabled": False,
                        "default_model": "",
                    },
                },
                "enabled": False,
            },
        )
        assert cleared.status_code == 200
        assert cleared.json()["has_api_key"] is False
        assert cleared.json()["masked_api_key"] == ""
        assert cleared.json()["is_ready"] is False
        assert cleared.json()["agent_model_overrides"] == {}


def test_llm_model_discovery_uses_saved_key_and_returns_models(tmp_path: Path, monkeypatch) -> None:
    client = build_client(tmp_path / "llm-discovery.db")

    class FakeResponse:
        status_code = 200
        text = ""
        reason_phrase = "OK"

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": [
                    {"id": "deepseek-chat", "owned_by": "deepseek"},
                    {"id": "deepseek-reasoner", "owned_by": "deepseek"},
                ]
            }

    def fake_get(url: str, *, headers: dict[str, str], timeout: float, follow_redirects: bool):  # type: ignore[no-untyped-def]
        assert url == "https://api.deepseek.com/v1/models"
        assert headers["Authorization"] == "Bearer sk-saved-discovery-key"
        assert timeout == 10.0
        assert follow_redirects is True
        return FakeResponse()

    monkeypatch.setattr("app.services.llm_config_service.httpx.get", fake_get)

    with client:
        headers = login_headers(client)
        configured = client.put(
            "/api/v1/llm-config",
            headers=headers,
            json={
                "provider_name": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1",
                "default_model": "deepseek-chat",
                "enabled": False,
                "agent_overrides": {
                    "backend_architect": {
                        "override_enabled": True,
                        "provider_name": "DeepSeek",
                        "base_url": "https://api.deepseek.com/v1",
                        "default_model": "deepseek-chat",
                        "api_key": "sk-saved-discovery-key",
                    }
                },
            },
        )
        assert configured.status_code == 200

        discovered = client.post(
            "/api/v1/llm-config/discover-models",
            headers=headers,
            json={
                "agent_code": "backend_architect",
                "provider_name": "DeepSeek",
                "base_url": "https://api.deepseek.com/v1",
            },
        )
        assert discovered.status_code == 200
        assert discovered.json()["used_saved_api_key"] is True
        assert [item["model_id"] for item in discovered.json()["models"]] == [
            "deepseek-chat",
            "deepseek-reasoner",
        ]


def test_auto_runtime_requires_llm_config_instead_of_silent_template_fallback(tmp_path: Path) -> None:
    client = build_client(
        tmp_path / "auto-runtime-requires-config.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "auto",
            "OPENAI_API_KEY": "",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
        },
    )

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Auto Runtime Validation Project",
            latest_requirement="需要验证 auto 模式在未配置模型时不会静默回退到模板草稿。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要验证 auto 模式在未配置模型时不会静默回退到模板草稿。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "FAILED"

        current = client.get(f"/api/v1/runs/{run_uid}", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)
        artifacts = client.get(f"/api/v1/projects/{project_uid}/artifacts", headers=headers)

        assert current.status_code == 200
        assert events.status_code == 200
        assert artifacts.status_code == 200
        assert artifacts.json() == []
        assert "静默回退" in current.json()["error_message"]
        assert any(event["event_type"] == "flow.failed" for event in events.json())


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
        runtime_settings = self.resolve_runtime_settings(agent_profile)
        captured_runtime["base_url"] = self.runtime_config.base_url if self.runtime_config else ""
        captured_runtime["api_key"] = self.runtime_config.api_key if self.runtime_config else ""
        captured_runtime[f"{agent_profile.agent_code}_agent_model"] = agent_profile.model
        captured_runtime[f"{agent_profile.agent_code}_resolved_model"] = runtime_settings.model
        captured_runtime[f"{agent_profile.agent_code}_resolved_base_url"] = runtime_settings.base_url
        captured_runtime[f"{agent_profile.agent_code}_resolved_api_key"] = runtime_settings.api_key
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
                "agent_overrides": {
                    "product_manager": {
                        "override_enabled": True,
                        "provider_name": "DeepSeek",
                        "base_url": "https://api.deepseek.com/v1",
                        "default_model": "deepseek-reasoner",
                        "api_key": "sk-role-runtime-9999",
                    }
                },
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
        assert captured_runtime["product_manager_agent_model"] == "gpt-4.1-mini"
        assert captured_runtime["product_manager_resolved_model"] == "deepseek-reasoner"
        assert captured_runtime["product_manager_resolved_base_url"] == "https://api.deepseek.com/v1"
        assert captured_runtime["product_manager_resolved_api_key"] == "sk-role-runtime-9999"
        assert any(
            event["payload_json"].get("runtime_mode") == "crewai"
            for event in events.json()
            if event["event_type"].startswith("task.")
        )

    import json
    import sqlite3

    with sqlite3.connect(tmp_path / "llm-config-auto.db") as connection:
        prompt_snapshot_text = connection.execute(
            "select prompt_snapshot from task_runs where agent_code='product_manager' order by id asc limit 1"
        ).fetchone()[0]

    prompt_snapshot = json.loads(prompt_snapshot_text)
    assert prompt_snapshot["runtime"]["model"] == "deepseek-reasoner"
    assert prompt_snapshot["runtime"]["base_url"] == "https://api.deepseek.com/v1"


def test_crewai_runner_prefers_agent_override_model() -> None:
    from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
    from app.orchestrators.runtime import CrewAIStageRunner
    from app.services.llm_config_service import RuntimeLLMConfig

    runner = CrewAIStageRunner(
        runtime_config=RuntimeLLMConfig(
            provider_name="OpenAI Compatible",
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            default_model="gpt-account-default",
            agent_model_overrides={"frontend_developer": "gpt-frontend-specialist"},
        )
    )

    resolved_model = runner.resolve_model_name(
        ResolvedAgentProfile(
            agent_code="frontend_developer",
            display_name="Frontend Developer",
            description="",
            model="gpt-role-fallback",
            temperature=0.2,
            allow_delegation=False,
            prompt_snapshot={},
        )
    )

    assert resolved_model == "gpt-frontend-specialist"


def test_crewai_runner_prefers_full_agent_runtime_override() -> None:
    from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
    from app.orchestrators.runtime import CrewAIStageRunner
    from app.services.llm_config_service import RuntimeAgentLLMConfig, RuntimeLLMConfig

    runner = CrewAIStageRunner(
        runtime_config=RuntimeLLMConfig(
            provider_name="OpenAI Compatible",
            base_url="https://api.example.com/v1",
            api_key="sk-account",
            default_model="gpt-account-default",
            agent_overrides={
                "frontend_developer": RuntimeAgentLLMConfig(
                    override_enabled=True,
                    provider_name="DeepSeek",
                    base_url="https://api.deepseek.com/v1",
                    api_key="sk-role",
                    default_model="deepseek-chat",
                )
            },
        )
    )

    runtime = runner.resolve_runtime_settings(
        ResolvedAgentProfile(
            agent_code="frontend_developer",
            display_name="Frontend Developer",
            description="",
            model="gpt-role-fallback",
            temperature=0.2,
            allow_delegation=False,
            prompt_snapshot={},
        )
    )

    assert runtime.provider_name == "DeepSeek"
    assert runtime.base_url == "https://api.deepseek.com/v1"
    assert runtime.api_key == "sk-role"
    assert runtime.model == "deepseek-chat"


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


def test_parallel_stage_quality_gate_failure_does_not_leave_running_tasks(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "parallel-quality-gate-failure.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    payloads = build_crewai_payloads()

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        payload = payloads[crew_name]
        if crew_name == "FrontendDesignCrew":
            payload = {
                **payload,
                "page_tree": payload["page_tree"][:1],
            }
        return CrewAIStageRunResult(
            payload=payload,
            raw_output=json.dumps(payload, ensure_ascii=False),
            prompt_tokens=32,
            completion_tokens=48,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Parallel Quality Gate Failure Project",
            latest_requirement="需要验证并行阶段失败后，不会留下 RUNNING 状态的任务记录。",
        )

        run = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要验证并行阶段失败后，不会留下 RUNNING 状态的任务记录。"},
        )
        assert run.status_code == 201
        run_uid = run.json()["run_uid"]

        final_status = wait_for_run_completion(client, headers, run_uid)
        assert final_status == "FAILED"

        tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)

        assert tasks.status_code == 200
        assert events.status_code == 200
        assert tasks.json()
        assert all(item["status"] in {"SUCCEEDED", "FAILED", "CANCELLED"} for item in tasks.json())
        assert any(item["step_code"] == "frontend_design" and item["status"] == "FAILED" for item in tasks.json())
        assert any(item["event_type"] == "flow.failed" for item in events.json())


def test_resume_run_clears_previous_attempt_records(tmp_path: Path, monkeypatch) -> None:
    client = build_client(
        tmp_path / "resume-clears-history.db",
        extra_env={
            "AGENT_RUNTIME_MODE": "crewai",
            "OPENAI_API_KEY": "test-key",
        },
    )

    from app.orchestrators.runtime import CrewAIStageRunResult, CrewAIStageRunner

    payloads = build_crewai_payloads()

    def fake_run_stage(self, *, crew_name, agent_profile, task_description, expected_output, output_model):  # type: ignore[no-untyped-def]
        payload = payloads[crew_name]
        if crew_name == "FrontendDesignCrew":
            payload = {
                **payload,
                "page_tree": payload["page_tree"][:1],
            }
        return CrewAIStageRunResult(
            payload=payload,
            raw_output=json.dumps(payload, ensure_ascii=False),
            prompt_tokens=32,
            completion_tokens=48,
        )

    monkeypatch.setattr(CrewAIStageRunner, "run_stage", fake_run_stage)

    with client:
        headers = login_headers(client)
        project_uid = create_project(
            client,
            headers,
            name="Resume Cleanup Project",
            latest_requirement="需要验证继续执行时会清掉旧的任务与事件记录。",
        )

        created = client.post(
            f"/api/v1/projects/{project_uid}/runs",
            headers=headers,
            json={"requirement_text": "需要验证继续执行时会清掉旧的任务与事件记录。"},
        )
        assert created.status_code == 201
        run_uid = created.json()["run_uid"]

        first_status = wait_for_run_completion(client, headers, run_uid)
        assert first_status == "FAILED"

        first_tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        first_events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)

        assert first_tasks.status_code == 200
        assert first_events.status_code == 200
        assert len(first_tasks.json()) == 5
        assert len(first_events.json()) >= 1

        resumed = client.post(f"/api/v1/runs/{run_uid}/resume", headers=headers)
        assert resumed.status_code == 200

        second_status = wait_for_run_completion(client, headers, run_uid)
        assert second_status == "FAILED"

        second_tasks = client.get(f"/api/v1/runs/{run_uid}/tasks", headers=headers)
        second_events = client.get(f"/api/v1/runs/{run_uid}/events", headers=headers)

        assert second_tasks.status_code == 200
        assert second_events.status_code == 200
        assert len(second_tasks.json()) == 5
        assert len({item["step_code"] for item in second_tasks.json()}) == 5
        assert any(item["event_type"] == "flow.started" for item in second_events.json())
        assert any(item["event_type"] == "flow.failed" for item in second_events.json())


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
    assert parsed["task_breakdown"]["priorities"] == [
        "先打通主链路",
        "保证阶段产物可审阅",
        "补齐运行观测能力",
    ]


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
