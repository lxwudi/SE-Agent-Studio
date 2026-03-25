# SE-Agent Studio 开发前技术设计文档

## 1. 文档定位

本文档只面向技术设计与开发实施，作为 SE-Agent Studio 第一阶段开发的直接依据。本文档不讨论课程答辩、选题意义、商业价值或市场分析，只回答以下问题：

1. 系统要如何拆分模块。
2. 现有 `agents/` 里的角色身份如何落到可执行的 Agent 配置。
3. CrewAI 的 `Flow / Crew / Agent / Task / Guardrail / Event Listener / Memory / Knowledge / Human Feedback` 应如何组合使用。
4. 后端、前端、数据库、异步执行、状态追踪、产物管理应如何实现。
5. 第一版开发范围应如何控制，哪些能力先做，哪些后做。

## 2. 设计目标与边界

### 2.1 目标

第一版系统需要达成以下技术目标：

1. 用户输入一段项目需求后，系统能够自动组织多个软件工程角色生成结构化技术产物。
2. 所有运行过程均可追踪，至少可以看到运行状态、阶段输出、错误信息和最终产物。
3. 每个阶段的输入输出必须结构化，不能依赖脆弱的自然语言后处理。
4. 多智能体编排逻辑必须可控、可复现、可逐步调试，不能把整个系统交给一个自由发挥的“总控 Agent”。
5. 前后端、任务执行、LLM 调用、提示词模板、结果存储必须解耦，便于后续替换模型、扩展角色和增加流程模板。

### 2.2 非目标

第一版不做以下能力：

1. 不做自由拖拽式流程编排器。
2. 不做自动生成完整项目代码并直接落库的复杂闭环。
3. 不做多租户 SaaS 级别的权限、审计和计费系统。
4. 不追求通用 Agent 平台，而是聚焦“软件工程技术文档生成与协作追踪”。

### 2.3 核心设计原则

1. **Flow First**：以 CrewAI Flow 作为运行时总控层，Crew 只负责完成阶段性工作单元。
2. **Schema First**：所有关键阶段必须使用 Pydantic 结构化输出。
3. **Fixed Workflow First**：首版采用固定模板流程，避免开放式编排导致的不稳定性。
4. **Persist Everything Important**：所有关键状态、事件、阶段输出、最终产物都要持久化。
5. **Prompt as Config**：角色人格和提示词模板配置化，不写死在业务代码里。
6. **Human Review Optional**：流程预留人工审核节点，但不依赖人工才能完成主流程。

## 3. 推荐总体方案

### 3.1 架构结论

推荐采用如下方案：

- 前端：`Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts`
- 后端 API：`FastAPI`
- 异步任务：`Celery + Redis`
- 数据库：`MySQL 8.0`
- 智能体编排：`CrewAI`
- 数据建模：`SQLAlchemy 2.x + Alembic + Pydantic`
- 实时状态：`SSE`，轮询作为降级方案
- 模型接入：统一 OpenAI 兼容接口适配层，兼容 OpenAI / DeepSeek / Qwen / 本地服务

### 3.2 架构分层

```text
+-------------------------------+
|           Web Frontend        |
| Project / Run / Artifact UI   |
+---------------+---------------+
                |
                v
+-----------------------------------------------+
|                FastAPI API Layer              |
| Auth / Project / Workflow / Run / Artifact    |
+----------------------+------------------------+
                       |
         +-------------+-------------+
         |                           |
         v                           v
+--------------------+     +----------------------+
| Application Layer  |     |   Streaming Layer    |
| Use Cases / DTOs   |     | SSE / Polling API    |
+---------+----------+     +----------+-----------+
          |                            |
          v                            |
+-----------------------------------------------+
|             Orchestration Layer               |
| Flow / Crew / Agent Factory / Guardrails      |
+----------------------+------------------------+
                       |
                       v
+-----------------------------------------------+
|                 Worker Layer                   |
| Celery Worker + CrewAI Runtime                |
+----------------------+------------------------+
                       |
     +-----------------+------------------+
     |                 |                  |
     v                 v                  v
+-----------+   +-------------+   +------------------+
|  MySQL    |   |    Redis    |   |  LLM Providers   |
| metadata  |   | queue/cache |   | OpenAI-compatible|
+-----------+   +-------------+   +------------------+
```

### 3.3 为什么不是“一个大 Crew 跑到底”

不推荐把所有角色直接塞进一个大 Crew 然后一次 `kickoff()` 跑完，原因如下：

1. 难以做阶段级状态追踪。
2. 难以插入人工审核、失败重试、条件分支。
3. 难以在前后端并行阶段做 fan-out / fan-in。
4. 难以把每个阶段的产物稳定持久化。
5. 整体失败时难以从中间状态恢复。

因此推荐模式为：

- `Flow` 负责流程图、状态、分支、并行、持久化、恢复和人工审核。
- `Crew` 负责完成一个明确的阶段性任务，如“需求结构化”“架构设计”“前后端方案生成”“测试方案生成”。
- `Agent` 负责角色能力与输出风格。

## 4. 角色体系设计：如何利用现有 agents 身份

当前仓库中已有如下角色定义：

1. `agents/product-manager.md`
2. `agents/engineering-software-architect.md`
3. `agents/engineering-backend-architect.md`
4. `agents/engineering-ai-engineer.md`
5. `agents/engineering-frontend-developer.md`
6. `agents/testing-api-tester.md`

这些文件不应仅作为静态提示词参考，而应作为系统内置 Agent 模板的来源。推荐做法如下：

1. 解析 Markdown Front Matter，提取 `name / description / vibe / tools` 等元数据。
2. 将正文主体视为 `backstory` 与角色行为规范来源。
3. 将文件内容同步到数据库中的 `agent_profile` 与 `prompt_template_version`。
4. 运行时通过 `AgentFactory` 将数据库配置映射为 CrewAI `Agent` 对象。

### 4.1 角色与系统职责映射

| 角色 | 技术定位 | 是否建议首版启用 | 主要输出 |
|------|----------|------------------|----------|
| Product Manager | 需求结构化与任务拆解 Agent | 是 | `RequirementSpec`、`FeatureList`、`TaskBreakdown` |
| Software Architect | 系统总体架构与 ADR Agent | 是 | `ArchitectureBlueprint`、`ADRList` |
| Backend Architect | 后端边界、数据模型、API 合同 Agent | 是 | `BackendDesign`、`EntityModel`、`ApiContractSet` |
| AI Engineer | LLM 接入、Prompt/RAG/Guardrail 设计 Agent | 是 | `AIIntegrationSpec`、`PromptPolicy`、`EvaluationPlan` |
| Frontend Developer | 前端 IA、页面结构、组件设计 Agent | 是 | `FrontendBlueprint`、`PageTree`、`InteractionSpec` |
| API Tester | 测试策略、接口测试、验收标准 Agent | 是 | `ApiTestPlan`、`AcceptanceCriteria`、`RiskChecklist` |

### 4.2 推荐角色使用策略

#### Product Manager

该角色虽然偏产品，但在本项目中仍然必须保留，因为“需求转结构化技术输入”本质上是技术编排的起点。首版中它不输出商业分析，而只输出：

1. 需求摘要
2. 功能点清单
3. 非功能约束
4. 优先级
5. 待澄清项

#### Software Architect

作为总体技术方案的主设计者，负责：

1. 模块划分
2. 部署架构
3. 关键技术选型
4. 组件依赖关系
5. ADR 列表

#### Backend Architect

负责把总体架构落到服务端实现层：

1. 领域边界
2. 数据模型
3. API 设计
4. 异步任务模型
5. 安全与性能约束

#### AI Engineer

这是本项目区别于普通课设系统的关键角色，建议不要省略。它不负责训练模型，而是负责：

1. 模型提供方适配
2. Prompt 模板管理策略
3. 输出 Schema 策略
4. Guardrail 与评估方案
5. Knowledge / Memory 使用方案
6. Token 成本与失败恢复策略

#### Frontend Developer

负责把后端产物中心和运行监控界面做成可实现的前端技术蓝图：

1. 页面信息架构
2. 页面与组件树
3. 状态管理切分
4. API 对接方式
5. 长任务监控与实时刷新方案

#### API Tester

不应只在最后生成几条测试样例，而应参与接口合同与验收标准设计：

1. 覆盖成功/失败/边界场景
2. 覆盖权限、频控、超时、幂等、空结果
3. 生成接口测试数据模板
4. 输出验收标准，供最终 review 阶段使用

### 4.3 是否要启用 allow_delegation

首版建议如下：

1. 大部分业务角色默认 `allow_delegation=False`
2. 只在少数“评审型 Crew”中启用 `allow_delegation=True`
3. 不建议在全局主流程中让 Agent 自由互相提问和分配任务

原因是：

1. 主流程稳定性优先于智能性。
2. 明确的 DAG 更便于追踪和重试。
3. 课程项目阶段更需要可解释和可展示的确定性结果。

## 5. CrewAI 编排设计

### 5.1 总原则

采用“Flow 负责总控，Crew 负责阶段工作，Agent 负责角色执行”的三层结构。

### 5.2 推荐主流程

```text
需求输入
  -> 需求结构化 Crew
  -> 需求校验路由
      -> 不完整：人工补充 / 自动重试
      -> 完整：进入架构设计 Crew
  -> 并行阶段
      -> 后端设计 Crew
      -> 前端设计 Crew
      -> AI 集成设计 Crew
  -> 汇聚阶段
      -> 测试设计 Crew
      -> 一致性评审 Crew
  -> 产物汇总与落库
```

### 5.3 为什么主流程要用 Flow

因为本项目天然需要以下能力，而这些能力更适合用 Flow 表达：

1. **阶段状态**：`PENDING / RUNNING / WAITING_REVIEW / FAILED / COMPLETED`
2. **条件分支**：需求不完整时插入补充节点
3. **并行分支**：后端、前端、AI 集成三个阶段可以并行
4. **汇聚**：使用 `and_()` 等待多个分支完成
5. **人工审核**：通过 `@human_feedback` 插入审批或修订循环
6. **持久化恢复**：通过 `@persist()` 或自定义 `FlowPersistence` 保存状态

### 5.4 推荐 Crew 划分

#### 1. RequirementAnalysisCrew

目标：把自然语言需求转成可供后续技术阶段使用的结构化规格。

成员：

1. Product Manager
2. Software Architect（轻量校验）

过程：

1. PM 生成需求结构化结果
2. 软件架构师补充技术约束与边界检查

输出：

- `RequirementSpec`
- `TaskBreakdown`
- `ClarificationList`

#### 2. ArchitectureDesignCrew

目标：形成系统总体架构与关键决策。

成员：

1. Software Architect
2. Backend Architect
3. AI Engineer

过程：

1. 软件架构师输出整体架构
2. 后端架构师补充后端边界与数据模型
3. AI 工程师补充 LLM 集成与执行约束

输出：

- `ArchitectureBlueprint`
- `ADRList`
- `SystemContext`

#### 3. BackendDesignCrew

目标：生成后端技术方案。

成员：

1. Backend Architect

输出：

- `BackendDesign`
- `EntityModel`
- `ApiContractSet`
- `RunStateDesign`

#### 4. FrontendDesignCrew

目标：生成前端技术方案。

成员：

1. Frontend Developer

输出：

- `FrontendBlueprint`
- `PageTree`
- `ComponentMap`
- `FrontendApiBindings`

#### 5. AIPlatformDesignCrew

目标：生成 AI 平台接入和运行时设计。

成员：

1. AI Engineer

输出：

- `AIIntegrationSpec`
- `PromptPolicy`
- `OutputSchemaRegistry`
- `EvaluationPlan`

#### 6. QualityAssuranceCrew

目标：基于前序产物生成测试与验收方案。

成员：

1. API Tester
2. Software Architect（评审）

输出：

- `ApiTestPlan`
- `AcceptanceCriteria`
- `TechnicalRiskList`

#### 7. ConsistencyReviewCrew

目标：做最终一致性检查，不再新增大范围设计。

成员：

1. Software Architect
2. API Tester
3. AI Engineer

建议使用：

- `Process.sequential` 作为首选
- `planning=True`
- 有需要时局部启用 `Process.hierarchical`

### 5.5 首版是否使用 hierarchical process

建议结论：

1. **主流程不用 hierarchical**
2. **局部评审 Crew 可尝试 hierarchical**

原因：

1. 主流程使用显式 Flow 更稳定。
2. hierarchical 更适合做“评审/统筹/再分配”而不是承担整个系统的生命周期控制。
3. 局部评审 Crew 中可以引入一个自定义 `TechLeadManager`，让其协调架构、测试、AI 工程角色进行交叉审查。

## 6. Flow 状态模型设计

推荐定义一个强类型 Flow State，而不是使用松散字典。

```python
from pydantic import BaseModel, Field
from typing import Any

class ProjectFlowState(BaseModel):
    id: str | None = None
    project_id: int
    flow_run_uid: str
    workflow_code: str
    requirement_text: str

    requirement_spec: dict[str, Any] | None = None
    task_breakdown: dict[str, Any] | None = None
    architecture_blueprint: dict[str, Any] | None = None
    backend_design: dict[str, Any] | None = None
    frontend_blueprint: dict[str, Any] | None = None
    ai_integration_spec: dict[str, Any] | None = None
    api_test_plan: dict[str, Any] | None = None
    review_summary: dict[str, Any] | None = None

    clarification_needed: bool = False
    review_required: bool = False
    current_stage: str = "created"
    artifact_ids: list[int] = Field(default_factory=list)
```

### 6.1 状态设计原则

1. 只存跨阶段必需数据。
2. 大文本正文保存到产物表，State 里保存结构化摘要和引用 ID。
3. 所有阶段结果同时存入：
   - Flow State
   - `task_run.output_json`
   - `artifact.content_json`

### 6.2 持久化策略

CrewAI 自带 `@persist()`，默认使用 SQLite 持久化。首版不建议直接把默认 SQLite 当成正式存储，而应采用两层策略：

1. Flow 内部保留 `@persist()` 能力，用于流程恢复实验与调试。
2. 业务正式数据统一落在 MySQL 中，由平台自己的 Repository 维护。

如果后续要深度使用 Flow 持久化，应实现自定义 `FlowPersistence` 适配层，把状态持久化到 MySQL 或 Redis。

## 7. 推荐 Flow 伪代码

```python
from crewai.flow.flow import Flow, start, listen, router, and_
from crewai.flow.persistence import persist

@persist()
class TechnicalDesignFlow(Flow[ProjectFlowState]):

    @start()
    def initialize_run(self):
        self.state.current_stage = "initializing"
        # 创建 flow_run / 记录初始事件
        return {"requirement_text": self.state.requirement_text}

    @listen(initialize_run)
    def run_requirement_crew(self):
        self.state.current_stage = "requirements"
        # RequirementAnalysisCrew kickoff
        return {"requirement_spec": "...", "clarification_needed": False}

    @router(run_requirement_crew)
    def route_requirement(self):
        if self.state.clarification_needed:
            return "needs_clarification"
        return "requirements_ok"

    @listen("needs_clarification")
    def wait_for_review_or_regenerate(self):
        self.state.current_stage = "waiting_clarification"
        # 人工补充 or 自动重试

    @listen("requirements_ok")
    def run_architecture_crew(self):
        self.state.current_stage = "architecture"

    @listen(run_architecture_crew)
    def run_backend_crew(self):
        self.state.current_stage = "backend_design"

    @listen(run_architecture_crew)
    def run_frontend_crew(self):
        self.state.current_stage = "frontend_design"

    @listen(run_architecture_crew)
    def run_ai_design_crew(self):
        self.state.current_stage = "ai_design"

    @listen(and_(run_backend_crew, run_frontend_crew, run_ai_design_crew))
    def run_quality_crew(self):
        self.state.current_stage = "quality_assurance"

    @listen(run_quality_crew)
    def run_consistency_review(self):
        self.state.current_stage = "consistency_review"

    @listen(run_consistency_review)
    def finalize_artifacts(self):
        self.state.current_stage = "completed"
```

## 8. 结构化输出设计

这是本项目成败的关键。所有核心阶段都必须输出固定 Schema。

### 8.1 关键输出模型

建议至少定义以下 Pydantic 模型：

1. `RequirementSpec`
2. `TaskBreakdown`
3. `ArchitectureBlueprint`
4. `ADRItem`
5. `BackendDesign`
6. `EntityDefinition`
7. `ApiEndpointContract`
8. `FrontendBlueprint`
9. `PageSpec`
10. `AIIntegrationSpec`
11. `ApiTestPlan`
12. `ConsistencyReviewSummary`

### 8.2 示例：RequirementSpec

```python
from pydantic import BaseModel

class RequirementSpec(BaseModel):
    project_name: str
    problem_statement: str
    target_users: list[str]
    core_features: list[str]
    non_functional_requirements: list[str]
    constraints: list[str]
    assumptions: list[str]
    open_questions: list[str]
```

### 8.3 示例：ArchitectureBlueprint

```python
class ArchitectureBlueprint(BaseModel):
    architecture_style: str
    core_modules: list[str]
    data_flow: list[str]
    deployment_units: list[str]
    key_decisions: list[str]
    risks: list[str]
```

### 8.4 Guardrail 设计

每个关键 Task 都应配置 guardrail，至少校验：

1. 必填字段是否齐全。
2. 列表字段是否为空。
3. 是否出现“未提供信息”“无法确定”这类占位内容。
4. 输出是否符合 JSON / Pydantic 约束。
5. 关键产物之间是否存在明显冲突。

例如：

- `RequirementSpec` 为空则不允许进入架构阶段
- `ApiContractSet` 与 `FrontendApiBindings` 接口名不一致则进入 review

## 9. Prompt 与 Agent 配置策略

### 9.1 配置来源

推荐以当前 `agents/*.md` 为默认模板源，但运行时不直接读取文件拼 prompt，而是采用以下结构：

1. 文件系统模板：项目内置默认版本
2. 数据库存档：管理员可启用某一版本
3. 运行时快照：某次运行实际使用的 prompt 需落到 `task_run.prompt_snapshot`

### 9.2 AgentFactory

后端实现 `AgentFactory`，负责：

1. 从 `agent_profile` 读取角色配置
2. 注入模型配置、温度、最大迭代次数、是否允许委派
3. 绑定工具、Knowledge、Memory、step callback
4. 生成 CrewAI `Agent`

### 9.3 Prompt 组装顺序

推荐顺序：

1. 系统保底规则
2. 角色 backstory
3. 当前任务 description
4. 结构化输出要求
5. 项目上下文与前序产物摘要
6. Guardrail 失败后的修复提示

## 10. 知识与记忆设计

### 10.1 是否需要 CrewAI Knowledge

需要，但首版只做受控使用。

建议场景：

1. 项目需求附件（Markdown、PDF、TXT）
2. 团队预置技术规范
3. 系统默认模板说明

推荐做法：

1. 用户上传文档后存储到项目附件目录
2. 运行某些 Crew 时根据需要构建 `knowledge_sources`
3. 仅对 Requirement / Architecture / QA 这类检索收益明显的阶段启用

### 10.2 是否需要 CrewAI Memory

需要，但也应受控。

建议使用策略：

1. 主流程 Flow 使用共享 memory 保存阶段性事实
2. 个别 Agent 可使用 scoped memory 保存私有推理事实
3. 不把 memory 当成正式业务存储，正式结果仍落库

### 10.3 记忆边界

避免以下问题：

1. 让历史项目记忆污染当前项目
2. 同一项目不同运行版本互相覆盖
3. 把未审核内容作为长期可信事实

因此推荐 scope 设计：

```text
/project/{project_uid}
/project/{project_uid}/run/{run_uid}
/project/{project_uid}/shared
/agent/{agent_code}
```

## 11. 事件监听与可观测性

### 11.1 为什么必须接入 Event Listener

仅依赖 Flow 最终结果不足以支撑运行监控页面。系统需要把 CrewAI 内部事件映射为平台可展示日志。

### 11.2 建议监听的事件

至少监听：

1. `CrewKickoffStartedEvent`
2. `TaskStartedEvent`
3. `TaskCompletedEvent`
4. `TaskFailedEvent`
5. `AgentExecutionCompletedEvent`
6. `ToolUsageStartedEvent`
7. `ToolUsageFinishedEvent`
8. `ToolUsageErrorEvent`

### 11.3 平台侧落库策略

定义 `run_event` 表，字段包括：

1. `flow_run_id`
2. `task_run_id`
3. `event_type`
4. `event_source`
5. `payload_json`
6. `created_at`

前端运行监控页通过：

1. SSE 实时读取增量事件
2. 页面初始化时拉取历史事件列表

### 11.4 观测面板

第一版至少展示：

1. 当前阶段
2. 已完成阶段数
3. 每阶段耗时
4. 失败原因
5. 主要产物入口
6. Token 使用统计

## 12. 运行时任务模型

### 12.1 为什么需要异步 Worker

CrewAI 任务天然是长时任务，不应在 API 请求线程里直接运行。

推荐链路：

1. 前端调用 `POST /runs`
2. API 创建 `flow_run` 记录
3. API 投递 Celery 任务
4. Worker 构建 Flow 并执行
5. Worker 通过事件监听器持续写入 MySQL / Redis
6. 前端通过 SSE 或轮询查看状态

### 12.2 状态机

#### flow_run.status

建议枚举：

1. `CREATED`
2. `QUEUED`
3. `RUNNING`
4. `WAITING_REVIEW`
5. `PARTIAL_FAILED`
6. `FAILED`
7. `COMPLETED`
8. `CANCELLED`

#### task_run.status

建议枚举：

1. `PENDING`
2. `RUNNING`
3. `RETRYING`
4. `SUCCEEDED`
5. `FAILED`
6. `SKIPPED`

### 12.3 重试策略

首版重试只做三类：

1. LLM 接口超时或临时错误：自动重试 1 到 2 次
2. Guardrail 不通过：按修复提示重新生成 1 次
3. 下游依赖缺失：不自动重试，直接标记失败

## 13. 数据库设计

### 13.1 实体列表

建议至少包含以下表：

1. `user`
2. `project`
3. `agent_profile`
4. `prompt_template_version`
5. `workflow_template`
6. `workflow_step`
7. `flow_run`
8. `task_run`
9. `run_event`
10. `artifact`
11. `artifact_version`
12. `llm_provider_config`
13. `project_attachment`

### 13.2 推荐表结构增强

相比原始课程方案，建议增加以下字段：

#### `agent_profile`

- `agent_code`
- `display_name`
- `source_file`
- `default_model`
- `temperature`
- `allow_delegation`
- `enabled`
- `meta_json`

#### `prompt_template_version`

- `agent_profile_id`
- `version`
- `system_prompt`
- `backstory_prompt`
- `rules_prompt`
- `created_at`

#### `workflow_template`

- `workflow_code`
- `name`
- `description`
- `version`
- `enabled`
- `config_json`

#### `workflow_step`

- `workflow_template_id`
- `step_code`
- `step_type`
- `agent_code`
- `depends_on`
- `parallel_group`
- `output_schema`
- `sort_order`

#### `flow_run`

- `run_uid`
- `project_id`
- `workflow_template_id`
- `status`
- `current_stage`
- `input_requirement`
- `state_json`
- `error_message`
- `started_at`
- `finished_at`

#### `task_run`

- `task_uid`
- `flow_run_id`
- `step_code`
- `agent_code`
- `crew_name`
- `input_json`
- `output_json`
- `output_text`
- `prompt_snapshot`
- `token_usage_prompt`
- `token_usage_completion`
- `status`
- `error_message`
- `started_at`
- `finished_at`

#### `artifact`

- `artifact_uid`
- `project_id`
- `flow_run_id`
- `artifact_type`
- `title`
- `content_markdown`
- `content_json`
- `source_task_run_id`
- `version_no`
- `created_at`

### 13.3 主键建议

为了兼顾易读性与 API 安全性，建议：

1. 内部主键使用 `BIGINT`
2. 对外暴露的运行 ID、产物 ID 使用 `uid` 字段（UUID）

## 14. API 设计

### 14.1 项目与运行接口

#### 项目

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_uid}`
- `PATCH /api/v1/projects/{project_uid}`

#### 流程运行

- `POST /api/v1/projects/{project_uid}/runs`
- `GET /api/v1/runs/{run_uid}`
- `GET /api/v1/runs/{run_uid}/tasks`
- `GET /api/v1/runs/{run_uid}/events`
- `POST /api/v1/runs/{run_uid}/cancel`
- `POST /api/v1/runs/{run_uid}/resume`

#### 产物

- `GET /api/v1/projects/{project_uid}/artifacts`
- `GET /api/v1/artifacts/{artifact_uid}`
- `GET /api/v1/artifacts/{artifact_uid}/export?format=md|pdf`

#### 管理后台

- `GET /api/v1/admin/agents`
- `PATCH /api/v1/admin/agents/{agent_code}`
- `GET /api/v1/admin/workflows`
- `PATCH /api/v1/admin/workflows/{workflow_code}`

### 14.2 实时更新接口

推荐：

- `GET /api/v1/runs/{run_uid}/stream`

实现方式：

1. 首选 SSE
2. 不可用时前端每 3 秒轮询一次 `GET /runs/{run_uid}`

## 15. 前端技术设计

### 15.1 页面结构

1. 登录页
2. 项目列表页
3. 项目详情页
4. 新建运行页
5. 运行监控页
6. 产物中心页
7. 管理配置页

### 15.2 关键前端状态

Pinia 中建议拆分：

1. `authStore`
2. `projectStore`
3. `runStore`
4. `artifactStore`
5. `adminConfigStore`

### 15.3 运行监控页重点

运行监控页必须能展示：

1. 主流程节点列表
2. 当前节点高亮
3. 每节点输入/输出摘要
4. 事件时间线
5. 失败重试信息
6. 产物快捷入口

### 15.4 产物中心页重点

按产物类型分组展示：

1. 需求规格
2. 架构设计
3. 后端设计
4. 前端设计
5. AI 集成设计
6. 测试计划
7. 最终技术汇总

## 16. 后端代码结构建议

推荐目录：

```text
backend/
  app/
    api/
      v1/
    core/
      config.py
      security.py
      logging.py
    db/
      base.py
      session.py
      models/
    schemas/
    repositories/
    services/
      project_service.py
      run_service.py
      artifact_service.py
    orchestrators/
      agents/
        agent_factory.py
      crews/
        requirement_crew.py
        architecture_crew.py
        backend_crew.py
        frontend_crew.py
        ai_platform_crew.py
        qa_crew.py
        consistency_review_crew.py
      flows/
        technical_design_flow.py
      listeners/
        platform_event_listener.py
      guardrails/
        requirement_guardrails.py
        architecture_guardrails.py
      outputs/
        requirement_models.py
        architecture_models.py
        frontend_models.py
        backend_models.py
        qa_models.py
    workers/
      celery_app.py
      tasks.py
```

## 17. 安全与配置设计

### 17.1 配置项

必须使用环境变量管理：

1. `DATABASE_URL`
2. `REDIS_URL`
3. `OPENAI_API_KEY`
4. `OPENAI_BASE_URL`
5. `DEFAULT_MODEL`
6. `JWT_SECRET`
7. `PDF_EXPORT_SERVICE_URL`（如有）

### 17.2 安全原则

1. 模型密钥不入库明文
2. 用户只能访问自己的项目、运行和产物
3. 管理员接口单独鉴权
4. Prompt 配置变更需要版本记录

## 18. 测试策略

### 18.1 单元测试

覆盖：

1. Pydantic 输出模型
2. Guardrail 函数
3. AgentFactory
4. Repository
5. 状态机转换

### 18.2 集成测试

覆盖：

1. 创建项目 -> 创建运行 -> Worker 执行 -> 产物落库
2. 失败重试与错误写入
3. SSE 事件输出
4. 导出接口

### 18.3 Prompt 回归测试

选取 3 到 5 条固定需求样例，检查：

1. 输出字段完整性
2. 关键产物长度
3. 前后阶段字段一致性
4. 失败率
5. token 开销

### 18.4 前端测试

1. 组件单元测试
2. 运行监控页交互测试
3. 关键流程 E2E 测试

## 19. 开发优先级

### 19.1 第一阶段必须完成

1. 项目管理
2. 固定流程模板
3. Flow + Worker 执行链路
4. 角色模板加载
5. 结构化输出
6. 运行追踪
7. 产物中心

### 19.2 第二阶段增强

1. 人工审核节点
2. Knowledge 附件检索
3. prompt 版本后台管理
4. 局部 hierarchical review crew
5. PDF 导出

### 19.3 第三阶段扩展

1. 自定义流程模板
2. 更多角色
3. 评估指标与质量评分
4. 更细粒度的成本分析

## 20. 关键结论

1. **可以充分利用现有 `agents/` 里的各种身份**，而且它们已经足够覆盖第一版所需的软件工程技术角色。
2. **CrewAI 非常适合本项目，但最佳用法不是“一个 Crew 跑完整个平台”**，而是“Flow 做总控，多个 Crew 做阶段工作”。
3. **首版最稳妥的路径是固定流程模板 + 结构化输出 + Worker 异步执行 + 事件追踪**。
4. **AI Engineer 角色建议纳入首版，而不是只保留产品、架构、前端、测试几个传统角色**，因为本项目本质上还有一层“LLM 系统工程”问题需要专门角色负责。
5. **hierarchical process 可以用，但只建议局部使用**；整个平台主流程仍以显式 Flow 控制最稳。

## 21. 第一版落地建议

如果马上进入开发，推荐按以下顺序实现：

1. 建立后端基础工程、数据库模型、用户/项目接口。
2. 建立 `AgentFactory`，先把现有 `agents/*.md` 转成可运行 Agent。
3. 先做 `RequirementAnalysisCrew` 和 `ArchitectureDesignCrew`。
4. 实现 `TechnicalDesignFlow` 与 Celery Worker。
5. 实现 `flow_run / task_run / run_event / artifact` 的完整落库链路。
6. 前端先完成项目页、运行监控页、产物中心页。
7. 再补 `BackendDesignCrew / FrontendDesignCrew / AIPlatformDesignCrew / QualityAssuranceCrew`。

这条路径可以最快形成可演示、可继续迭代的最小闭环。

## 22. 八人团队分工方案

以下分工基于本文档的推荐架构进行设计，原则是：

1. 每个核心模块只有一个第一负责人。
2. 前后端、编排层、运行时、测试层可以并行推进。
3. 每个人都要有明确可交付成果，避免出现“参与但无 owner”的情况。
4. 分工尽量按模块边界切，而不是按零散页面或零散接口切。

### 22.1 团队角色总览

| 成员 | 推荐角色 | 第一负责模块 | 主要交付物 |
|------|----------|--------------|------------|
| 1 | 技术负责人 / 软件架构 Owner | 总体技术方案、接口边界、集成验收 | ADR、接口基线、联调节奏、技术评审 |
| 2 | AI 编排工程师 | CrewAI 编排层 | AgentFactory、Crews、Flow、Guardrails |
| 3 | 后端业务工程师 | FastAPI 业务接口层 | 认证、项目、运行、产物 API |
| 4 | 后端运行时工程师 | Worker / 事件 / 基础设施 | Celery、Redis、SSE、事件监听、部署脚本 |
| 5 | 前端基础工程师 | 前端基础框架与项目管理页 | Vue 脚手架、路由、Pinia、项目页 |
| 6 | 前端业务工程师 | 运行监控页与产物中心 | 运行监控、事件时间线、产物展示 |
| 7 | 测试与质量工程师 | 测试体系与质量门禁 | API 测试、E2E、验收用例、缺陷管理 |
| 8 | 全栈配置与导出工程师 | 管理后台、附件、导出 | Agent/Workflow 配置页、上传、导出 |

### 22.2 详细分工

#### 成员 1：技术负责人 / 软件架构 Owner

负责内容：

1. 维护总体技术方案、模块边界和命名规范。
2. 主导数据库核心模型和输出 Schema 的最终评审。
3. 负责跨模块接口冻结，包括前后端 API、Flow State、Artifact Schema。
4. 组织每周技术 review 和集成检查。
5. 负责 `ConsistencyReviewCrew` 的设计和最终技术一致性验收。

建议 owner 文件范围：

1. 架构文档与 ADR
2. `backend/app/orchestrators/outputs/*`
3. `backend/app/orchestrators/crews/consistency_review_crew.py`
4. 公共规范文档、接口约定文档

主要交付物：

1. 技术基线文档
2. 数据模型和 API 契约评审版
3. 集成 checklist
4. 最终技术验收报告

#### 成员 2：AI 编排工程师

负责内容：

1. 将 `agents/*.md` 转为系统内置 Agent 模板。
2. 实现 `AgentFactory`，支持角色配置、模型参数、prompt 组装。
3. 实现各个 Crew：
   - `RequirementAnalysisCrew`
   - `ArchitectureDesignCrew`
   - `BackendDesignCrew`
   - `FrontendDesignCrew`
   - `AIPlatformDesignCrew`
   - `QualityAssuranceCrew`
4. 实现 `TechnicalDesignFlow`。
5. 实现 Guardrail 和结构化输出校验逻辑。

建议 owner 文件范围：

1. `backend/app/orchestrators/agents/*`
2. `backend/app/orchestrators/crews/*`
3. `backend/app/orchestrators/flows/*`
4. `backend/app/orchestrators/guardrails/*`

主要交付物：

1. Agent 模板加载器
2. CrewAI 编排层主代码
3. Pydantic 输出模型接入
4. Flow 运行主链路

#### 成员 3：后端业务工程师

负责内容：

1. 搭建 FastAPI 基础工程。
2. 实现用户认证、项目管理、运行查询、产物查询等 REST API。
3. 实现 `schemas / services / repositories` 三层业务结构。
4. 负责 MySQL 模型落地和 Alembic 迁移。
5. 对接成员 2、4、8 输出的运行数据、配置数据和导出接口。

建议 owner 文件范围：

1. `backend/app/api/*`
2. `backend/app/schemas/*`
3. `backend/app/services/*`
4. `backend/app/repositories/*`
5. `backend/app/db/models/*`

主要交付物：

1. API 文档
2. 数据库实体和迁移脚本
3. 项目 / 运行 / 产物核心 CRUD
4. 基础鉴权能力

#### 成员 4：后端运行时工程师

负责内容：

1. 搭建 Celery Worker 和 Redis 任务链路。
2. 实现运行状态推进和 `flow_run / task_run / run_event` 写入。
3. 实现 CrewAI Event Listener 到平台事件表的映射。
4. 实现 SSE 推送和轮询兜底接口支撑。
5. 负责 Docker Compose、本地开发环境、日志和运行脚本。

建议 owner 文件范围：

1. `backend/app/workers/*`
2. `backend/app/orchestrators/listeners/*`
3. `backend/app/core/logging.py`
4. Docker / 部署脚本 / 本地运行脚本

主要交付物：

1. 异步任务执行链路
2. 实时状态推送能力
3. 运行日志和事件追踪
4. 一键启动开发环境

#### 成员 5：前端基础工程师

负责内容：

1. 初始化 Vue 3 + TypeScript + Vite 工程。
2. 搭建路由、Pinia、Axios 请求封装、基础布局。
3. 实现登录页、项目列表页、项目详情页、新建运行页。
4. 实现基础组件和全局状态结构。
5. 和成员 3 对齐基础 API 调用模型。

建议 owner 文件范围：

1. `frontend/src/router/*`
2. `frontend/src/stores/*`
3. `frontend/src/layouts/*`
4. `frontend/src/views/project/*`
5. `frontend/src/api/base.ts`

主要交付物：

1. 前端基础工程
2. 项目管理相关页面
3. 通用请求层与状态管理
4. 页面骨架与导航体系

#### 成员 6：前端业务工程师

负责内容：

1. 实现运行监控页。
2. 实现事件时间线、阶段进度、阶段详情抽屉。
3. 实现产物中心页和产物详情页。
4. 实现运行统计图表和结果查看交互。
5. 与成员 4 对接 SSE，与成员 3 对接运行与产物接口。

建议 owner 文件范围：

1. `frontend/src/views/run/*`
2. `frontend/src/views/artifact/*`
3. `frontend/src/components/timeline/*`
4. `frontend/src/components/flow-graph/*`

主要交付物：

1. 运行监控页
2. 产物中心页
3. 事件时间线
4. 统计展示组件

#### 成员 7：测试与质量工程师

负责内容：

1. 设计测试基线和测试目录结构。
2. 编写后端单元测试、API 集成测试。
3. 编写前端关键流程 E2E 测试。
4. 维护验收用例、缺陷单、回归测试清单。
5. 重点验证结构化输出、状态流转、异常处理、接口一致性。

建议 owner 文件范围：

1. `backend/tests/*`
2. `frontend/tests/*`
3. `e2e/*`
4. 测试报告与缺陷清单

主要交付物：

1. 测试计划
2. 自动化测试脚本
3. 冒烟回归清单
4. 验收报告

#### 成员 8：全栈配置与导出工程师

负责内容：

1. 实现管理员配置页，包括 Agent 配置、Workflow 配置。
2. 实现附件上传、项目附件列表、运行输入补充能力。
3. 实现 Markdown 导出，若时间允许再补 PDF 导出。
4. 对接成员 2 的 Agent/Profile 配置和成员 3 的后台管理接口。
5. 辅助做系统集成、环境配置和答辩演示版本整理。

建议 owner 文件范围：

1. `backend/app/api/admin/*`
2. `backend/app/services/admin_*`
3. `frontend/src/views/admin/*`
4. `frontend/src/views/export/*`
5. 上传与导出相关模块

主要交付物：

1. 管理后台
2. 附件与导出功能
3. 配置管理功能
4. 可演示版本整理

### 22.3 推荐协作关系

建议按以下方式建立固定协作对子：

1. 成员 1 对接 2、3、5，负责接口和模型评审。
2. 成员 2 对接 3、4、8，负责编排层与配置层打通。
3. 成员 3 对接 5、6，负责 API 契约同步。
4. 成员 4 对接 6、7，负责状态流、日志流、测试环境。
5. 成员 7 全程穿插到 2、3、4、5、6 的开发中，不放到最后才介入。
6. 成员 8 作为全栈补位，优先支援最晚完成的模块。

### 22.4 六周开发节奏建议

#### 第 1 周：基线确定

1. 成员 1 完成架构、模块边界、接口冻结第一版。
2. 成员 2 完成 Agent 模板解析、输出 Schema 草案。
3. 成员 3 完成后端工程初始化、数据库设计初版。
4. 成员 4 完成 Celery/Redis/Docker 骨架。
5. 成员 5 完成前端脚手架、路由、布局。
6. 成员 6 完成运行监控页和产物中心页原型。
7. 成员 7 完成测试计划和用例框架。
8. 成员 8 完成管理后台和导出模块设计稿。

#### 第 2 周：核心骨架开发

1. 成员 2 完成 `RequirementAnalysisCrew`、`ArchitectureDesignCrew`。
2. 成员 3 完成项目、运行、产物基础 API。
3. 成员 4 完成 Worker 投递和运行状态写入。
4. 成员 5 完成项目管理页面。
5. 成员 6 完成运行监控页静态版。
6. 成员 8 完成后台配置和附件上传基础功能。

#### 第 3 周：主链路打通

1. 成员 2 完成 `TechnicalDesignFlow` 主链路。
2. 成员 3、4 打通 `POST /runs -> Worker -> flow_run/task_run`。
3. 成员 5、6 打通前端创建运行和查看状态。
4. 成员 7 开始首轮 API 自动化测试。
5. 成员 8 接入 Agent/Workflow 配置读写能力。

#### 第 4 周：并行模块补齐

1. 成员 2 完成 `BackendDesignCrew / FrontendDesignCrew / AIPlatformDesignCrew / QualityAssuranceCrew`。
2. 成员 4 完成事件监听和 SSE。
3. 成员 6 完成事件时间线和产物中心联动。
4. 成员 8 完成 Markdown 导出与附件管理。
5. 成员 7 完成集成测试与前端 E2E 初版。

#### 第 5 周：联调与收敛

1. 全员进入联调。
2. 成员 1 主持技术验收和冲突清理。
3. 成员 7 主导缺陷分级和回归。
4. 成员 8 协助演示流程、导出流程和管理后台稳定性整理。

#### 第 6 周：稳定化与答辩版本

1. 修复高优先级缺陷。
2. 补齐演示数据和示例项目。
3. 完成部署脚本、运行说明、测试报告。
4. 形成可答辩版本。

### 22.5 管理建议

为了避免 8 个人项目最后变成 2 个人收尾，建议强制执行以下规则：

1. 每个模块必须有 owner 和 backup。
2. 所有接口先写契约，再并行开发。
3. 每周至少两次集成，不允许拖到最后一周统一联调。
4. 成员 7 的测试环境和回归结果必须在群里透明同步。
5. 成员 1 负责控制范围，超出第一版目标的需求统一进入延期列表。
