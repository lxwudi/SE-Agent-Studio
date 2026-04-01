# SE-Agent Studio 技术设计文档

## 1. 文档定位

本文档重点回答以下问题：

1. 当前系统的产品定位和运行边界是什么。
2. 多智能体编排层、后端、前端、状态追踪、产物管理现在如何协作。
3. 哪些设计原则仍然成立，哪些能力已经从“计划中”变成“已实现”。
4. 当前版本还保留了哪些明确边界和未完成项。

## 2. 当前目标与边界

### 2.1 当前目标

当前版本的核心目标已经从“只生成技术设计文档”扩展为“两类固定工作流”：

1. `technical_design_v1`：生成结构化技术设计产物。
2. `delivery_v1`：生成可运行 starter 项目、执行基础验证，并提供项目压缩包下载。

因此，平台当前承担的是“软件工程多智能体协同交付”的最小闭环，而不再只是设计文档工作台。

### 2.2 当前边界

当前版本仍然保留以下边界：

1. 仍然以固定工作流为主，不支持自由拖拽式流程编排。
2. `delivery_v1` 当前以可运行 starter 交付为主，还不是对任意现有仓库做稳定增量改造的通用代码代理。
3. 人工审核、知识检索、长期记忆能力保留设计入口，但不是当前主链路的核心能力。
4. PDF 导出、多租户审计计费、复杂权限域隔离还未作为当前主目标完成。

### 2.3 仍然有效的核心原则

以下原则在当前实现中依然成立：

1. **Flow First**：流程总控仍然由 Flow 承担。
2. **Schema First**：关键阶段输出仍然要求结构化模型。
3. **Fixed Workflow First**：优先保证固定流程稳定可用，再考虑开放式编排。
4. **Persist Everything Important**：关键状态、事件、任务结果、产物都要落库。
5. **Prompt as Config**：角色模板、运行时模型配置、提示词快照都配置化。
6. **Zip First for Delivery**：交付场景优先给用户可下载、可运行的项目结果，而不是只展示内部文档。

## 3. 当前总体方案

### 3.1 架构结论

当前仓库的实际技术栈如下：

- 前端：`Vue 3 + TypeScript + Vite + Pinia + Element Plus`
- 后端 API：`FastAPI`
- 编排层：`CrewAI`
- 数据建模：`SQLAlchemy 2.x + Alembic + Pydantic`
- 本地默认数据库：`SQLite`
- 本地默认执行模式：`thread`
- 可选执行模式：`Celery + Redis`
- 模型接入：兼容 `OpenAI API` 的云端接口

和旧版设计最大的差异是：

1. 本地默认启动不再依赖 `MySQL + Redis + Celery`。
2. 运行时支持账号级和角色级独立模型配置。
3. 工作流已经从单一 `technical_design_v1` 扩展为 `technical_design_v1 + delivery_v1`。

### 3.2 当前分层

```text
+-------------------------------+
|           Web Frontend        |
| Project / Run / Artifact UI   |
+---------------+---------------+
                |
                v
+-----------------------------------------------+
|                FastAPI API Layer              |
| Auth / Project / Run / Artifact / LLM Config  |
+----------------------+------------------------+
                       |
         +-------------+-------------+
         |                           |
         v                           v
+--------------------+     +----------------------+
| Application Layer  |     |   Streaming Layer    |
| Services / Repos   |     | SSE / Polling API    |
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
|              Runtime Dispatch Layer           |
| thread mode / Celery worker / template fallback|
+----------------------+------------------------+
                       |
     +-----------------+------------------+
     |                 |                  |
     v                 v                  v
+-----------+   +-------------+   +------------------+
| SQLite /  |   |  Event Log   |   |  LLM Providers   |
|  MySQL    |   |  + Artifacts |   | OpenAI-compatible|
+-----------+   +-------------+   +------------------+
```

### 3.3 为什么仍然不是“一个大 Crew 跑到底”

这一点没有变化，当前仍然不推荐把整个平台塞进一个大 Crew 一次性执行。

原因仍然成立：

1. 阶段级状态难追踪。
2. 并行和汇聚难控制。
3. 失败重试和恢复点难落地。
4. 前端无法稳定展示过程和结果。
5. 交付场景下还需要把代码文件、验证结果、工作区路径单独收敛出来。

因此当前实现依旧采用：

- `Flow` 负责总控、阶段路由、并行编排和状态推进。
- `Crew` 负责一个明确阶段的任务执行。
- `Agent` 负责角色行为、提示词和模型配置。

## 4. 角色体系与配置策略

### 4.1 当前启用角色

当前系统内置并启用的软件工程角色如下：

1. `product_manager`
2. `software_architect`
3. `backend_architect`
4. `frontend_developer`
5. `ai_engineer`
6. `api_tester`

### 4.2 角色职责

这些角色的职责边界仍然有效：

| 角色 | 当前主要职责 | 常见输出 |
|------|--------------|----------|
| Product Manager | 需求结构化、交付范围整理 | `RequirementSpec`、`DeliveryRequirementSpec` |
| Software Architect | 总体架构、方案收敛、最终移交总结 | `ArchitectureBlueprint`、`SolutionDeliveryPlan`、`DeliveryHandoff` |
| Backend Architect | 后端设计或后端代码包生成 | `BackendDesign`、`CodeBundle` |
| Frontend Developer | 前端设计或前端代码包生成 | `FrontendBlueprint`、`CodeBundle` |
| AI Engineer | AI 集成方案、运行策略设计 | `AIIntegrationSpec` |
| API Tester | 验证方案、集成检查、验收结果 | `ApiTestPlan`、`IntegrationBundle` |

### 4.3 角色模板与模型配置的关系

当前实现中，角色模板和模型配置的关系已经明确分层：

1. 角色模板保存角色身份、默认模型、提示词版本和是否启用。
2. 账号默认模型配置提供全局兜底的 `provider / base_url / api_key / model`。
3. 每个角色都可以再单独配置自己的 `provider / base_url / api_key / model`。
4. 运行时优先使用角色独立配置，缺失字段再回退到账号默认配置。

当前优先级为：

1. 角色独立配置中的模型、URL、API Key
2. 账号默认配置
3. 角色模板默认模型
4. 系统全局默认模型

### 4.4 allow_delegation

这一条原则仍然保留：

1. 大多数业务角色默认仍以可控、确定性执行为主。
2. 主流程不依赖角色之间自由委派来驱动状态推进。
3. 系统稳定性优先于过度自治。

## 5. 当前工作流设计

### 5.1 工作流总览

当前平台内置两个固定工作流：

#### `technical_design_v1`

面向“结构化技术设计”场景，主链路为：

```text
需求结构化
  -> 架构设计
  -> 并行设计
      -> 后端设计
      -> 前端设计
      -> AI 集成设计
  -> 测试方案
  -> 一致性评审
```

#### `delivery_v1`

面向“可运行 starter 交付”场景，主链路为：

```text
交付需求
  -> 方案设计
  -> 并行交付
      -> 后端代码包
      -> 前端代码包
  -> 集成验证
  -> 交付移交
```

### 5.2 为什么保留双工作流

当前保留双工作流是合理的：

1. `technical_design_v1` 适合做设计探索、方案比对、前置文档沉淀。
2. `delivery_v1` 适合把需求快速收敛为可运行 starter 和压缩包交付。
3. 二者共享角色模板、任务模型、事件体系和产物体系，但目标不同。

### 5.3 `delivery_v1` 的当前定位

`delivery_v1` 当前已经具备以下能力：

1. 生成交付需求和实施方案。
2. 生成前后端 starter 代码包。
3. 将文件物化到仓库根目录下的 `.delivery-workspaces/<run_uid>/`。
4. 自动执行基础验证，并把验证结果写入产物。
5. 对最近一次成功交付提供项目压缩包下载。

同时也要明确当前边界：

1. 它优先保证“能交付、能跑、能下载”，而不是对任意项目做高自治编码。
2. 当前仍然允许在 AI 运行不稳定时回退到确定性模板路径。

## 6. Flow 状态、任务与产物模型

### 6.1 当前 Flow State

项目仍然采用强类型 Flow State，而不是完全依赖松散字典。

当前状态模型既覆盖设计流，也覆盖交付流：

```python
class ProjectFlowState(BaseModel):
    project_id: int
    flow_run_uid: str
    workflow_code: str
    requirement_text: str

    requirement_spec: dict | None = None
    architecture_blueprint: dict | None = None
    backend_design: dict | None = None
    frontend_blueprint: dict | None = None
    ai_integration_spec: dict | None = None
    api_test_plan: dict | None = None
    review_summary: dict | None = None

    delivery_requirements: dict | None = None
    delivery_plan: dict | None = None
    backend_code_bundle: dict | None = None
    frontend_code_bundle: dict | None = None
    integration_bundle: dict | None = None
    delivery_handoff: dict | None = None

    current_stage: str = "created"
    artifact_ids: list[int] = []
```

### 6.2 状态设计原则

这一部分依然有效：

1. 只在 State 中保存跨阶段必需数据。
2. 大文本正文和最终结果落到产物表。
3. 阶段结果同时会体现在：
   - Flow State
   - `task_run.output_json`
   - `artifact.content_json`

### 6.3 运行时实体

当前核心运行实体包括：

1. `flow_run`
2. `task_run`
3. `run_event`
4. `artifact`

各自职责如下：

| 实体 | 作用 |
|------|------|
| `flow_run` | 表示一次完整工作流运行，记录状态、当前阶段、错误信息、起止时间 |
| `task_run` | 表示某个阶段的执行结果，记录输入、输出、提示词快照、token 统计 |
| `run_event` | 记录可观测事件，用于运行监控页和排障 |
| `artifact` | 记录最终面向用户查看或下载的产物 |

### 6.4 当前状态机

当前状态机设计仍然成立：

#### `flow_run.status`

1. `CREATED`
2. `QUEUED`
3. `RUNNING`
4. `WAITING_REVIEW`
5. `PARTIAL_FAILED`
6. `FAILED`
7. `COMPLETED`
8. `CANCELLED`

#### `task_run.status`

1. `PENDING`
2. `RUNNING`
3. `RETRYING`
4. `SUCCEEDED`
5. `FAILED`
6. `SKIPPED`

## 7. 持久化与执行模式

### 7.1 当前推荐执行方式

旧文档把 `Celery + Redis + MySQL` 写成了默认方案，这一点已经不再适用。

当前更准确的表述是：

1. 本地默认推荐 `SQLite + thread`，用于最快开发启动。
2. 需要多进程或队列化执行时，再切换到 `Celery + Redis`。
3. 数据库层支持开发期用 `SQLite`，也支持切换到 `MySQL`。

### 7.2 当前持久化策略

当前实现更偏向“平台自己的业务持久化优先”：

1. 正式状态以平台数据库中的 `flow_run / task_run / run_event / artifact` 为准。
2. Flow 自带持久化能力可以作为实验或扩展方向，但不是当前正式数据来源。
3. 交付工作区落在仓库根目录 `.delivery-workspaces/<run_uid>/`，并通过项目打包接口导出为 zip。

## 8. 结构化输出设计

### 8.1 设计流关键输出

以下结构化输出仍然有效：

1. `RequirementSpec`
2. `TaskBreakdown`
3. `ArchitectureBlueprint`
4. `BackendDesign`
5. `FrontendBlueprint`
6. `AIIntegrationSpec`
7. `ApiTestPlan`
8. `ConsistencyReviewSummary`

### 8.2 交付流关键输出

当前新增并已经落地的交付输出包括：

1. `DeliveryRequirementSpec`
2. `SolutionDeliveryPlan`
3. `CodeBundle`
4. `IntegrationBundle`
5. `DeliveryHandoff`
6. `VerificationResult`
7. `GeneratedFile`
8. `CommandSpec`

### 8.3 Guardrail 设计原则

以下 guardrail 原则仍然成立：

1. 必填字段必须齐全。
2. 列表字段不能全部为空。
3. 不允许明显占位文本直接进入下游阶段。
4. 输出必须满足 JSON / Pydantic 约束。
5. 跨阶段产物间要做一致性检查。

在当前交付流中，这套机制还会延伸到：

1. 启动命令和验证命令是否完整。
2. 生成文件列表是否齐全。
3. 自动验证是否通过。
4. 修复后是否真正收敛为成功结果。

## 9. Prompt、AgentFactory 与模型运行时

### 9.1 配置来源

这一部分仍然有效，但现在已经更完整：

1. `agents/*.md` 仍然是默认角色模板源。
2. 模板会同步到数据库中的 `agent_profile` 和 `prompt_template_version`。
3. 某次运行实际使用的提示词快照会写入 `task_run.prompt_snapshot`。
4. 用户可以在产品内配置账号级和角色级模型运行参数。

### 9.2 AgentFactory 的职责

`AgentFactory` 仍然负责：

1. 从角色配置读取角色身份和默认参数。
2. 组装角色提示词、规则和运行上下文。
3. 注入模型配置、温度、是否允许委派等参数。
4. 构造 CrewAI `Agent` 实例。

### 9.3 提示词组装顺序

仍建议按以下顺序组装：

1. 系统保底规则
2. 角色 backstory
3. 当前任务 description
4. 结构化输出要求
5. 项目上下文与前序产物摘要
6. 失败修复提示

### 9.4 当前模型配置能力

这是旧版设计中没有完整覆盖、但当前已经实现的部分：

1. 用户可配置账号默认 `provider / base_url / api_key / model`。
2. 每个角色可单独配置自己的 `provider / base_url / api_key / model`。
3. 页面可通过 `/models` 读取可用模型列表。
4. 当账号默认关闭时，已独立配置完整的角色仍可继续运行。

## 10. 事件监听与可观测性

### 10.1 为什么仍然必须有事件层

这个结论没有变化。只看 Flow 最终结果仍然不够，平台还必须记录过程事件，才能支撑：

1. 运行监控页
2. 阶段耗时统计
3. 失败原因追踪
4. 自动修复过程展示
5. 交付验证结果展示

### 10.2 建议监听与落库的信息

当前平台侧依旧需要记录：

1. 阶段开始
2. 阶段完成
3. 阶段失败
4. 自动验证开始与结束
5. 自动修复开始与结束
6. LLM 调用或工具调用的关键摘要事件

### 10.3 前端观测面板的最小要求

当前前端运行页至少应提供：

1. 当前阶段
2. 阶段进度
3. 任务明细
4. 事件时间线
5. 验证结果
6. 交付工作区路径或项目下载入口

## 11. API 设计

### 11.1 当前核心接口

当前后端 API 已经稳定在以下几组能力：

#### 认证

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`

#### 系统

- `GET /api/v1/health`
- `GET /api/v1/me`

#### 项目

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_uid}`
- `PATCH /api/v1/projects/{project_uid}`
- `DELETE /api/v1/projects/{project_uid}`
- `GET /api/v1/projects/{project_uid}/package`

#### 运行

- `POST /api/v1/projects/{project_uid}/runs`
- `GET /api/v1/runs/{run_uid}`
- `GET /api/v1/runs/{run_uid}/tasks`
- `GET /api/v1/runs/{run_uid}/events`
- `POST /api/v1/runs/{run_uid}/cancel`
- `POST /api/v1/runs/{run_uid}/resume`
- `GET /api/v1/runs/{run_uid}/stream`

#### 产物

- `GET /api/v1/projects/{project_uid}/artifacts`
- `GET /api/v1/artifacts/{artifact_uid}`
- `GET /api/v1/artifacts/{artifact_uid}/export`

#### 模型配置

- `GET /api/v1/llm-config`
- `PUT /api/v1/llm-config`
- `POST /api/v1/llm-config/discover-models`

#### 管理配置

- `GET /api/v1/admin/agents`
- `PATCH /api/v1/admin/agents/{agent_code}`
- `GET /api/v1/admin/workflows`
- `PATCH /api/v1/admin/workflows/{workflow_code}`

### 11.2 交付相关接口约定

当前交付相关的接口设计原则与旧版不同：

1. 用户优先拿到项目压缩包，而不是先阅读长篇设计文档。
2. 细节页仍然保留，用于排障、核对验证结果和查看产物。
3. 如果项目存在最近一次成功的 `delivery_v1` 运行，项目级接口应能直接返回 zip。

## 12. 前端设计

### 12.1 当前页面结构

当前保留并实际使用的页面包括：

1. 登录页
2. 项目列表页
3. 项目详情页
4. 运行监控页
5. 产物中心页
6. 模型配置页
7. 管理配置页

### 12.2 当前前端状态划分

Pinia 仍然建议围绕以下领域划分：

1. 认证
2. 项目
3. 运行
4. 产物
5. 管理配置
6. 模型配置

### 12.3 当前用户体验原则

这一部分相较旧版已经更新，当前更应强调：

1. 交付结果优先，而不是内部过程优先。
2. 项目详情页和运行页都应优先提供“下载项目压缩包”。
3. 监控信息用于排障，不应压过最终交付入口。
4. 返回上一级导航必须稳定，不依赖浏览器历史偶然性。

## 13. 后端代码结构建议

当前目录结构中仍然有效的骨架如下：

```text
backend/
  app/
    api/
      v1/
    core/
    db/
      models/
    schemas/
    repositories/
    services/
    orchestrators/
      agents/
      crews/
      flows/
      listeners/
      guardrails/
      outputs/
      runtime/
    workers/
```

与旧版相比，当前更准确的变化是：

1. `runtime/` 已成为独立目录，用于运行时模型解析和执行调度。
2. `flows/` 下不再只有 `technical_design_flow.py`，还包括 `delivery_flow.py`。
3. `workers/` 仍然保留，但本地默认启动并不强依赖 Celery worker。

## 14. 安全与配置设计

### 14.1 关键配置项

当前关键配置项包括：

1. `DATABASE_URL`
2. `EXECUTION_MODE`
3. `REDIS_URL`
4. `OPENAI_API_KEY`
5. `OPENAI_BASE_URL`
6. `DEFAULT_MODEL`
7. `AGENT_RUNTIME_MODE`
8. `JWT_SECRET`
9. `SECRET_ENCRYPTION_KEY`

### 14.2 安全原则

以下原则仍然成立：

1. 模型密钥不明文存储。
2. 用户只能访问自己的项目、运行和产物。
3. 管理员接口单独鉴权。
4. Prompt 和角色配置变更要保留版本和状态。
5. 角色独立 API Key 与账号默认 API Key 都要可掩码展示、可清空。

## 15. 测试策略

### 15.1 仍然有效的测试层次

当前仍然需要以下测试层次：

1. 输出模型和 guardrail 的单元测试
2. Repository / Service 的单元测试
3. API 冒烟与集成测试
4. 工作流主链路测试
5. 前端类型检查和关键页面回归测试

### 15.2 当前应重点覆盖的能力

和旧版相比，当前测试重点已经变化为：

1. `delivery_v1` 能否产出完整 starter
2. 自动验证和自动修复链路能否收敛
3. 项目删除是否正确级联
4. 项目打包下载是否正常
5. 模型配置和角色独立模型配置是否生效
6. 线程模式和 Celery 模式下的运行一致性

## 16. 当前未完成项

为了避免把现状写得过满，下面这些能力仍应明确标记为“未完全完成”：

1. `delivery_v1` 目前还是 starter 交付优先，还不是成熟的任意仓库自治代码代理。
2. 模板兜底仍然存在，说明 AI 生成稳定性还在持续收敛中。
3. PDF 导出尚未正式实现。
4. 人工审核、附件知识检索、长期记忆还没有成为当前核心闭环。
5. 更细粒度的成本统计、质量评分和多租户治理仍属于后续增强项。

## 17. 结论

当前版本可以这样概括：

1. 这已经不是“只生成技术设计文档”的系统。
2. 它已经是一个以固定工作流驱动的多智能体软件工程交付平台雏形。
3. 设计流和交付流并存，是当前系统最重要的结构变化。
4. 本地默认运行方式已经切换为 `SQLite + thread`，`Celery + Redis + MySQL` 不再是默认前提。
5. 角色模板、账号模型配置、角色独立模型配置共同构成了当前运行时配置体系。

这份文档后续应继续作为“当前实现说明”和“下一阶段设计基线”，而不是保留旧版那种“开发前假设稿”写法。
