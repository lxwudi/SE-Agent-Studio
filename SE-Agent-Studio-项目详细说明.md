# SE-Agent Studio 项目详细说明文档

> 文档版本：V1.0  
> 编写日期：2026-04-29  
> 适用范围：项目汇报、需求评审、技术设计交接、开发启动、测试验收与后续维护

## 1. 项目概述

SE-Agent Studio 是一个面向软件工程全流程的多智能体协作开发平台。项目目标是把传统软件工程中的需求整理、系统设计、前后端方案、AI 集成、测试验收、交付归档等工作，放入一个可追踪、可复用、可验证的协同工作台中。

用户在系统中创建项目并录入需求后，平台会按照预设的软件工程流程调度不同职责的智能体，例如产品经理、系统架构师、后端架构师、前端开发工程师、AI 工程师、API 测评师等。每个阶段会生成结构化产物，同时将运行过程、任务状态、事件记录和最终文档沉淀到项目空间中，方便查看、导出、复用和验收。

项目当前已经形成一个可运行的第一版系统，包含 FastAPI 后端、Vue 3 前端、数据库迁移、默认角色模板、固定工作流、登录鉴权、项目管理、运行监控、产物中心、模型配置和管理配置等核心能力。

## 2. 建设背景

在软件工程课程或真实团队协作中，项目从需求到交付往往存在以下问题：

- 需求文档、设计文档、测试文档分散，缺少统一管理入口。
- 不同岗位之间的交接依赖口头沟通，过程难以追踪。
- 需求、设计、代码和测试之间容易出现不一致。
- 项目阶段产物缺少版本记录，后期复盘成本较高。
- 多智能体生成内容如果没有流程约束，容易变成零散输出，难以纳入工程管理。

SE-Agent Studio 的设计思路是用“工作流 + 多角色智能体 + 结构化产物 + 运行事件”的方式，把项目过程变成一个可管理的闭环。系统不是简单聊天工具，而是一个围绕软件工程交付过程建立的项目工作台。

## 3. 项目目标

### 3.1 总体目标

构建一个可以支持软件工程项目从需求输入到交付产物归档的多智能体协作平台，使项目需求、流程、任务、代码产物和验证结果能够在同一个系统中集中管理。

### 3.2 具体目标

- 支持用户登录并进入独立的项目空间。
- 支持创建项目、维护项目背景和需求描述。
- 支持按固定流程启动多阶段智能体任务。
- 支持实时查看运行状态、阶段进展和任务事件。
- 支持保存每个阶段生成的 Markdown 与结构化 JSON 产物。
- 支持查看项目产物中心，并导出 Markdown 结果。
- 支持下载项目交付包。
- 支持用户自助配置 OpenAI 兼容模型接口。
- 支持管理员维护智能体配置和工作流配置。
- 支持本地开发环境快速启动，也支持后续切换到 MySQL、Redis、Celery 的部署形态。

## 4. 非目标说明

当前版本重点是打通软件工程多智能体协作的主流程，不把以下内容作为第一阶段重点：

- 不做复杂的多租户组织管理。
- 不做完整的企业权限矩阵，例如部门、团队、审批链。
- 不做真正的代码仓库自动提交和自动发布。
- 不做完整 PDF 导出，当前 PDF 导出接口仍处于规划状态。
- 不追求一次性覆盖所有软件工程文档模板，而是优先覆盖需求、设计、测试和交付闭环。
- 不让 AI 完全替代项目成员，系统定位是辅助整理、生成、验证和归档。

## 5. 目标用户

| 用户类型 | 使用目标 | 典型操作 |
| --- | --- | --- |
| 项目负责人 | 管理项目、启动流程、查看总体进展 | 创建项目、录入需求、查看运行状态、下载交付包 |
| 系统分析师 | 整理业务需求和功能需求 | 编写需求背景、用户场景、功能需求、约束条件 |
| 系统架构师 | 负责系统设计和技术方案 | 查看需求产物、生成架构蓝图、维护工作流配置 |
| 程序员 | 基于产物理解实现范围 | 查看后端设计、前端设计、代码交付包 |
| 系统测评师 | 负责测试计划和验收验证 | 查看测试方案、检查验收标准、确认运行结果 |
| 管理员 | 维护智能体和流程模板 | 配置 Agent、配置 Workflow、控制启停 |

## 6. 项目职责分工建议

结合本项目的文档类型和现有角色配置，建议按以下方式分工。

### 6.1 需求规格说明书

需求规格说明书建议由系统分析师主责，项目经理负责范围控制、进度协调和评审组织。

两位系统分析师可以这样分工：

| 成员 | 主要负责内容 | 输出重点 |
| --- | --- | --- |
| 系统分析师 A | 项目背景、业务目标、用户角色、业务流程、功能性需求、用例说明 | 把“用户要什么、业务怎么跑、功能有哪些”讲清楚 |
| 系统分析师 B | 运行环境、外部接口、数据需求、非功能需求、约束条件、异常处理、验收口径 | 把“系统边界、质量要求、可测标准和限制条件”讲清楚 |

### 6.2 系统设计说明书

系统设计说明书建议由系统架构师主责。系统架构师根据需求规格说明书，进一步拆解系统架构、模块边界、数据库设计、接口设计、部署设计和关键技术决策。

程序员提供实现可行性反馈，系统测评师补充测试性和验收性要求，项目经理负责组织设计评审。

### 6.3 开发与测试职责

| 职务 | 主要职责 |
| --- | --- |
| 项目经理 | 控制范围、进度、风险、人员分工和评审节奏 |
| 系统架构师 | 负责总体架构、关键技术选型、接口边界和系统设计说明书 |
| 系统分析师 | 负责需求调研、需求规格说明书、用例和非功能需求 |
| 程序员 | 负责前后端功能实现、接口联调、缺陷修复 |
| 系统测评师 | 负责测试计划、接口测试、验收测试和质量报告 |

## 7. 核心业务流程

### 7.1 用户侧主流程

```mermaid
flowchart TD
    A["用户登录系统"] --> B["进入项目空间"]
    B --> C["创建项目并录入需求"]
    C --> D["选择并启动工作流"]
    D --> E["系统创建运行记录"]
    E --> F["多智能体分阶段执行"]
    F --> G["生成任务事件与阶段产物"]
    G --> H["用户在运行监控页查看进度"]
    H --> I["用户在产物中心查看与导出结果"]
    I --> J["下载项目交付包或进入下一轮迭代"]
```

### 7.2 系统内部执行流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant FE as Vue 前端
    participant API as FastAPI 后端
    participant DB as 数据库
    participant Runner as Flow Runner
    participant Agent as CrewAI/Template Agent

    U->>FE: 提交项目需求
    FE->>API: POST /projects/{project_uid}/runs
    API->>DB: 创建 FlowRun，状态 QUEUED
    API->>Runner: thread 或 Celery 投递运行
    Runner->>DB: 创建 TaskRun，记录 prompt 快照
    Runner->>Agent: 执行当前阶段任务
    Agent-->>Runner: 返回结构化结果
    Runner->>DB: 保存 TaskRun、Artifact、RunEvent
    FE->>API: SSE 订阅 /runs/{run_uid}/stream
    API-->>FE: 推送运行状态和事件
    U->>FE: 查看产物、导出 Markdown
```

## 8. 当前已实现功能

### 8.1 登录与用户

- 用户通过邮箱和密码登录。
- 登录成功后获得 JWT 访问令牌。
- 前端通过受保护路由控制访问。
- 默认管理员账号由后端环境变量配置。

默认账号：

| 项 | 值 |
| --- | --- |
| 邮箱 | `demo@se-agent.studio` |
| 密码 | `ChangeMe123!` |

正式部署前必须修改默认账号密码和 `JWT_SECRET`。

### 8.2 项目管理

- 创建项目。
- 查看项目列表。
- 查看项目详情。
- 更新项目信息。
- 删除项目。
- 保存项目最新需求。
- 下载项目交付包。

项目是系统的核心上下文，运行记录、任务记录和阶段产物都归属于项目。

### 8.3 工作流运行

系统当前支持两个固定工作流：

| 工作流编码 | 名称 | 目标 |
| --- | --- | --- |
| `technical_design_v1` | 技术设计固定流程 V1 | 从需求结构化到架构、前后端、AI、测试和一致性评审 |
| `delivery_v1` | 代码交付固定流程 V1 | 从交付需求到实施方案、前后端代码包、集成和移交 |

运行状态包括：

| 状态 | 含义 |
| --- | --- |
| `CREATED` | 已创建但尚未投递 |
| `QUEUED` | 已排队等待执行 |
| `RUNNING` | 正在执行 |
| `COMPLETED` | 执行完成 |
| `FAILED` | 执行失败 |
| `CANCELLED` | 用户取消 |

### 8.4 运行监控

- 查询运行详情。
- 查询阶段任务列表。
- 查询运行事件列表。
- 通过 SSE 获取运行事件和状态更新。
- 支持取消运行。
- 支持恢复失败或取消的运行。

每次阶段执行都会形成 `TaskRun`，系统会保存该阶段的输入、输出、状态、错误信息、token 估算和 prompt 快照。

### 8.5 产物中心

- 按项目查看所有阶段产物。
- 查看单个产物详情。
- 导出 Markdown。
- 产物同时保存 Markdown 内容和结构化 JSON 内容。

产物类型示例：

- 需求规格说明
- 系统架构蓝图
- 后端技术设计
- 前端技术蓝图
- AI 平台集成设计
- 测试与验收方案
- 一致性评审总结
- 后端代码交付包
- 前端代码交付包
- 集成交付说明
- 交付总结与移交

### 8.6 模型配置

用户可以在产品内配置自己的 OpenAI 兼容模型接口。

可配置项包括：

- 服务名称
- `base_url`
- 默认模型
- API Key
- 启用状态
- 不同智能体的模型覆盖配置
- 不同智能体的运行参数覆盖配置

模型配置优先级：

1. 用户在系统中保存并启用的模型配置。
2. 服务端 `.env` 中的 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。
3. 根据 `AGENT_RUNTIME_MODE` 决定是否使用模板模式。

### 8.7 管理配置

管理员可以管理：

- 智能体角色配置。
- 智能体 prompt 模板版本。
- 工作流模板。
- 工作流步骤。
- 工作流启用状态。

## 9. 多智能体角色设计

系统从 `agents/` 目录读取角色模板，并同步到数据库中的 `agent_profiles` 表。当前角色包括：

| Agent Code | 角色名称 | 主要职责 |
| --- | --- | --- |
| `product_manager` | Product Manager | 需求澄清、范围定义、用户价值和验收标准 |
| `software_architect` | Software Architect | 总体架构、模块边界、技术决策、一致性评审 |
| `backend_architect` | Backend Architect | 后端服务边界、数据模型、API 合同、异步策略 |
| `frontend_developer` | Frontend Developer | 页面结构、组件设计、前端状态、接口绑定 |
| `ai_engineer` | AI Engineer | 模型接入、prompt 策略、输出结构、AI 安全约束 |
| `api_tester` | API Tester | 接口测试、验收标准、风险清单、质量保障 |

这些角色不是简单的显示文本，而是会参与工作流阶段调度。后端在执行每个阶段时，会根据 `WorkflowStep.agent_code` 找到对应智能体配置，并组装当前阶段的 prompt、上下文和输出 schema。

## 10. 工作流阶段设计

### 10.1 技术设计工作流

`technical_design_v1` 适合从项目需求生成系统设计和测试方案。

| 顺序 | 阶段编码 | 负责角色 | 阶段产物 |
| --- | --- | --- | --- |
| 1 | `requirements` | `product_manager` | 需求规格说明 |
| 2 | `architecture` | `software_architect` | 系统架构蓝图 |
| 3 | `backend_design` | `backend_architect` | 后端技术设计 |
| 4 | `frontend_design` | `frontend_developer` | 前端技术蓝图 |
| 5 | `ai_design` | `ai_engineer` | AI 平台集成设计 |
| 6 | `quality_assurance` | `api_tester` | 测试与验收方案 |
| 7 | `consistency_review` | `software_architect` | 一致性评审总结 |

其中后端设计、前端设计和 AI 设计属于设计类并行阶段的候选，当前代码支持通过 `parallel_group` 表达并行提示。

### 10.2 代码交付工作流

`delivery_v1` 适合根据需求生成可运行的起步代码包和交付说明。

| 顺序 | 阶段编码 | 负责角色 | 阶段产物 |
| --- | --- | --- | --- |
| 1 | `delivery_requirements` | `product_manager` | 交付需求规格 |
| 2 | `solution_design` | `software_architect` | 交付实施方案 |
| 3 | `backend_delivery` | `backend_architect` | 后端代码交付包 |
| 4 | `frontend_delivery` | `frontend_developer` | 前端代码交付包 |
| 5 | `integration` | `api_tester` | 集成交付说明 |
| 6 | `handoff` | `software_architect` | 交付总结与移交 |

交付工作流支持模板兜底。当用户没有配置真实模型时，系统仍可生成确定性的示例交付产物，方便本地演示和流程联调。

## 11. 系统架构

### 11.1 总体架构

```mermaid
flowchart LR
    subgraph Client["前端层"]
        Vue["Vue 3 + TypeScript"]
        Pinia["Pinia 状态管理"]
        Element["Element Plus UI"]
    end

    subgraph API["服务层"]
        FastAPI["FastAPI REST/SSE"]
        Auth["JWT 鉴权"]
        Services["业务服务"]
        Flow["工作流编排"]
    end

    subgraph Runtime["执行层"]
        Thread["Thread 本地执行"]
        Celery["Celery Worker"]
        CrewAI["CrewAI Runtime"]
        Template["Template Runtime"]
    end

    subgraph Data["数据层"]
        SQLite["SQLite 本地开发"]
        MySQL["MySQL 正式/队列模式"]
        Redis["Redis Broker"]
    end

    Vue --> FastAPI
    Pinia --> FastAPI
    Element --> Vue
    FastAPI --> Auth
    FastAPI --> Services
    Services --> Flow
    Flow --> Thread
    Flow --> Celery
    Thread --> CrewAI
    Thread --> Template
    Celery --> CrewAI
    Celery --> Template
    Services --> SQLite
    Services --> MySQL
    Celery --> Redis
```

### 11.2 前端架构

前端位于 `frontend/`，技术栈如下：

| 技术 | 用途 |
| --- | --- |
| Vue 3 | 页面和组件开发 |
| TypeScript | 类型约束 |
| Vite | 开发服务器和构建工具 |
| Pinia | 前端状态管理 |
| Vue Router | 路由管理 |
| Element Plus | 基础 UI 组件 |
| Axios | HTTP 请求 |
| ECharts | 数据可视化能力 |

主要页面路由：

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | 登录页 | 用户登录 |
| `/projects` | 项目空间 | 查看项目列表、创建项目 |
| `/projects/:projectUid` | 项目详情 | 查看项目详情并启动流程 |
| `/runs/:runUid` | 运行监控 | 查看阶段进度、事件和任务 |
| `/projects/:projectUid/artifacts` | 产物中心 | 查看项目所有产物 |
| `/settings/llm` | 模型配置 | 配置 OpenAI 兼容接口 |
| `/admin` | 管理配置 | 管理智能体和工作流 |

前端模块划分：

| 目录 | 说明 |
| --- | --- |
| `src/api/` | 后端接口封装 |
| `src/stores/` | Pinia 状态管理 |
| `src/views/` | 页面级组件 |
| `src/components/` | 通用业务组件 |
| `src/layouts/` | 应用布局 |
| `src/utils/` | 下载、展示和交付工具函数 |
| `src/styles.css` | 全局视觉样式 |

### 11.3 后端架构

后端位于 `backend/`，技术栈如下：

| 技术 | 用途 |
| --- | --- |
| FastAPI | REST API、SSE 接口 |
| SQLAlchemy 2.x | ORM 和数据库访问 |
| Alembic | 数据库迁移 |
| Pydantic | 请求响应模型和配置管理 |
| PyJWT | JWT 登录令牌 |
| Celery | 异步任务队列 |
| Redis | Celery Broker 和结果后端 |
| CrewAI | 真实智能体运行时 |
| uv | Python 依赖管理 |

后端目录划分：

| 目录 | 说明 |
| --- | --- |
| `app/api/` | API 路由和依赖注入 |
| `app/core/` | 配置、日志、安全、枚举 |
| `app/db/` | 数据库会话和 ORM 模型 |
| `app/repositories/` | 数据访问层 |
| `app/services/` | 业务服务层 |
| `app/orchestrators/` | 工作流、智能体、运行时、输出模型 |
| `app/workers/` | Celery worker 和任务入口 |
| `alembic/` | 数据库迁移脚本 |
| `scripts/` | 初始化和数据引导脚本 |
| `tests/` | 自动化测试 |

### 11.4 分层职责

```mermaid
flowchart TD
    A["API Router"] --> B["Service"]
    B --> C["Repository"]
    C --> D["SQLAlchemy Model"]
    B --> E["Flow Orchestrator"]
    E --> F["Agent Factory"]
    E --> G["CrewAI Stage Runner"]
    E --> H["Template Handler"]
    E --> I["Artifact Renderer"]
```

| 层 | 职责 |
| --- | --- |
| API Router | 处理 HTTP 请求、鉴权依赖、响应模型 |
| Service | 封装项目、运行、产物、配置等业务逻辑 |
| Repository | 封装数据库读写 |
| Orchestrator | 负责编排多阶段工作流 |
| Agent Factory | 解析智能体配置和 prompt 快照 |
| Runtime | 调用真实 CrewAI 或模板兜底逻辑 |
| Model | 数据库实体和结构化输出模型 |

## 12. 数据模型

### 12.1 核心实体

```mermaid
erDiagram
    USER ||--o{ PROJECT : owns
    USER ||--o| USER_LLM_CONFIG : configures
    PROJECT ||--o{ FLOW_RUN : has
    PROJECT ||--o{ ARTIFACT : owns
    FLOW_RUN ||--o{ TASK_RUN : contains
    FLOW_RUN ||--o{ RUN_EVENT : emits
    FLOW_RUN ||--o{ ARTIFACT : produces
    AGENT_PROFILE ||--o{ PROMPT_TEMPLATE_VERSION : has
    WORKFLOW_TEMPLATE ||--o{ WORKFLOW_STEP : contains
```

### 12.2 实体说明

| 实体 | 表名 | 说明 |
| --- | --- | --- |
| User | `users` | 用户与管理员账号 |
| Project | `projects` | 项目基本信息、需求文本、状态 |
| FlowRun | `flow_runs` | 一次工作流运行记录 |
| TaskRun | `task_runs` | 工作流中单个阶段的任务记录 |
| RunEvent | `run_events` | 运行过程事件 |
| Artifact | `artifacts` | 阶段产物，保存 Markdown 和 JSON |
| AgentProfile | `agent_profiles` | 智能体角色配置 |
| PromptTemplateVersion | `prompt_template_versions` | prompt 模板版本 |
| WorkflowTemplate | `workflow_templates` | 工作流模板 |
| WorkflowStep | `workflow_steps` | 工作流步骤 |
| UserLLMConfig | `user_llm_configs` | 用户模型配置 |

### 12.3 数据流说明

- 用户创建项目后，系统保存项目名称、摘要、需求文本和状态。
- 用户启动工作流后，系统创建 `FlowRun`，并把运行状态设为 `QUEUED`。
- 执行器开始运行后，系统依次创建 `TaskRun`。
- 每个阶段执行成功后，系统创建对应 `Artifact`。
- 运行过程中的关键节点会写入 `RunEvent`。
- 前端通过轮询或 SSE 展示 `FlowRun`、`TaskRun` 和 `RunEvent`。

## 13. API 接口说明

除根级健康检查 `/healthz` 外，后端业务 API 默认前缀为 `/api/v1`。

### 13.1 系统与鉴权

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/health` | API 健康检查 |
| `GET` | `/healthz` | 应用根级健康检查 |
| `POST` | `/auth/login` | 用户登录 |
| `GET` | `/auth/me` | 获取当前登录用户 |
| `GET` | `/me` | 获取当前登录用户简要信息 |

### 13.2 项目接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/projects` | 创建项目 |
| `GET` | `/projects` | 获取项目列表 |
| `GET` | `/projects/{project_uid}` | 获取项目详情 |
| `PATCH` | `/projects/{project_uid}` | 更新项目 |
| `DELETE` | `/projects/{project_uid}` | 删除项目 |
| `GET` | `/projects/{project_uid}/package` | 下载项目交付包 |

### 13.3 运行接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/projects/{project_uid}/runs` | 创建工作流运行 |
| `GET` | `/runs/{run_uid}` | 获取运行详情 |
| `GET` | `/runs/{run_uid}/tasks` | 获取运行阶段任务 |
| `GET` | `/runs/{run_uid}/events` | 获取运行事件 |
| `GET` | `/runs/{run_uid}/stream` | SSE 实时运行流 |
| `POST` | `/runs/{run_uid}/cancel` | 取消运行 |
| `POST` | `/runs/{run_uid}/resume` | 恢复失败或取消的运行 |

### 13.4 产物接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/projects/{project_uid}/artifacts` | 获取项目产物列表 |
| `GET` | `/artifacts/{artifact_uid}` | 获取产物详情 |
| `GET` | `/artifacts/{artifact_uid}/export?format=md` | 导出 Markdown 产物 |

### 13.5 模型配置接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/llm-config` | 获取当前用户模型配置 |
| `PUT` | `/llm-config` | 更新当前用户模型配置 |
| `POST` | `/llm-config/discover-models` | 探测可用模型 |

### 13.6 管理接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/admin/agents` | 获取智能体配置列表 |
| `PATCH` | `/admin/agents/{agent_code}` | 更新智能体配置 |
| `GET` | `/admin/workflows` | 获取工作流配置列表 |
| `PATCH` | `/admin/workflows/{workflow_code}` | 更新工作流配置 |

## 14. 运行模式设计

### 14.1 执行模式

系统通过 `EXECUTION_MODE` 控制运行投递方式。

| 模式 | 配置值 | 说明 | 适用场景 |
| --- | --- | --- | --- |
| 本地线程模式 | `thread` | 后端进程内启动后台线程执行任务 | 本地开发、课程演示 |
| 队列模式 | `celery` | 投递到 Celery Worker 执行 | 正式部署、多任务运行 |

### 14.2 Agent 运行模式

系统通过 `AGENT_RUNTIME_MODE` 控制智能体执行方式。

| 模式 | 配置值 | 说明 |
| --- | --- | --- |
| 自动模式 | `auto` | 有模型配置时使用 CrewAI，否则按工作流策略处理 |
| 模板模式 | `template` | 使用本地模板生成确定性结果 |
| 真实模式 | `crewai` | 强制使用 CrewAI 和模型接口 |

技术设计流程在 `auto` 模式下，如果没有可用模型配置，会阻止运行，避免用户误以为模板草稿是真实 AI 结果。交付流程为了演示闭环，允许在没有模型配置时使用模板兜底。

## 15. 配置说明

后端配置来自 `backend/.env`，主要配置项如下：

| 配置项 | 说明 |
| --- | --- |
| `APP_NAME` | 后端应用名称 |
| `API_V1_PREFIX` | API 前缀，默认 `/api/v1` |
| `DATABASE_URL` | 数据库连接 |
| `REDIS_URL` | Redis 连接 |
| `DEFAULT_MODEL` | 默认模型名称 |
| `OPENAI_API_KEY` | 服务端默认模型 API Key |
| `OPENAI_BASE_URL` | OpenAI 兼容接口地址 |
| `SECRET_ENCRYPTION_KEY` | 用户 API Key 加密密钥 |
| `AGENT_RUNTIME_MODE` | 智能体运行模式 |
| `EXECUTION_MODE` | 任务执行模式 |
| `JWT_SECRET` | JWT 签名密钥 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 登录令牌有效期 |
| `AUTO_CREATE_SCHEMA` | 启动时是否自动建表 |
| `BOOTSTRAP_DATA_ON_STARTUP` | 启动时是否自动初始化默认数据 |
| `CORS_ORIGINS` | 前端跨域白名单 |
| `DEFAULT_OWNER_EMAIL` | 默认管理员邮箱 |
| `DEFAULT_OWNER_PASSWORD` | 默认管理员密码 |

## 16. 本地启动说明

### 16.1 后端本地启动

```bash
cd backend
cp .env.example .env
```

建议本地开发时把 `.env` 改成：

```env
DATABASE_URL=sqlite:///./.runtime/se_agent_studio.db
EXECUTION_MODE=thread
AGENT_RUNTIME_MODE=auto
```

启动命令：

```bash
uv sync --extra ai-runtime --extra dev
uv run alembic upgrade head
uv run python scripts/bootstrap_data.py
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端地址：

- API：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/healthz`

### 16.2 前端本地启动

```bash
cd frontend
pnpm install
pnpm dev --host 127.0.0.1 --port 5173
```

前端地址：

```text
http://127.0.0.1:5173/
```

### 16.3 MySQL + Redis + Celery 模式

当需要接近正式部署的队列执行方式时，启动依赖：

```bash
docker compose up -d mysql redis
```

后端配置示例：

```env
DATABASE_URL=mysql+pymysql://se_agent:se_agent@127.0.0.1:3306/se_agent_studio
EXECUTION_MODE=celery
REDIS_URL=redis://localhost:6379/0
```

启动 Web API：

```bash
cd backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动 Worker：

```bash
cd backend
uv run celery -A app.workers.celery_app:celery_app worker --loglevel=info
```

## 17. 安全设计

当前版本已经实现基础安全能力：

- 密码使用 PBKDF2-SHA256 哈希，迭代次数为 600000。
- 登录后签发 JWT，后端通过 `Authorization: Bearer <token>` 鉴权。
- API Key 不以明文保存，使用 Fernet 加密后写入数据库。
- 用户 API Key 展示时进行脱敏。
- 管理接口要求管理员身份。
- 用户只能访问自己拥有的项目、运行和产物。
- CORS 来源通过环境变量控制。

正式部署前必须处理：

- 修改默认管理员密码。
- 设置强随机 `JWT_SECRET`。
- 设置独立的 `SECRET_ENCRYPTION_KEY`。
- 使用 HTTPS。
- 限制 CORS 到正式前端域名。
- 对模型调用增加更细的限流、审计和成本控制。

## 18. 质量保障

### 18.1 已有验证方式

前端：

```bash
cd frontend
pnpm exec vue-tsc --noEmit
pnpm build
```

后端：

```bash
cd backend
python -m compileall app alembic
pytest tests/test_api_smoke.py
```

### 18.2 后端 Smoke Test 覆盖内容

当前后端测试围绕主链路设计，覆盖：

- 登录鉴权。
- 创建项目。
- 创建运行。
- 等待运行完成。
- 查询任务和事件。
- 查看产物。
- 交付包生成。
- 模板运行模式。
- CrewAI 模拟运行模式。

### 18.3 后续测试建议

- 增加前端组件测试。
- 增加端到端测试，覆盖登录、创建项目、启动运行、查看产物。
- 增加真实模型调用失败、超时、格式错误的恢复测试。
- 增加权限测试，确保用户无法访问他人项目。
- 增加 Celery 模式下的任务恢复和重复投递测试。
- 增加 API Key 加密密钥变化后的异常处理测试。

## 19. 当前项目目录说明

```text
SE-Agent-Studio/
├── README.md
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── orchestrators/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── workers/
│   ├── alembic/
│   ├── scripts/
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── utils/
│   │   └── views/
│   ├── public/
│   └── package.json
├── agents/
├── crewAI/
├── compose.yaml
├── docker-compose.yml
├── pnpm-workspace.yaml
└── pnpm-lock.yaml
```

## 20. 主要代码模块说明

### 20.1 后端关键模块

| 文件或目录 | 说明 |
| --- | --- |
| `backend/app/main.py` | FastAPI 应用入口 |
| `backend/app/core/config.py` | 配置读取和校验 |
| `backend/app/core/security.py` | 密码哈希、JWT、密钥加解密 |
| `backend/app/api/v1/` | v1 API 路由 |
| `backend/app/services/project_service.py` | 项目业务逻辑 |
| `backend/app/services/run_service.py` | 运行创建、投递、取消、恢复 |
| `backend/app/services/artifact_service.py` | 产物查询和导出 |
| `backend/app/services/llm_config_service.py` | 模型配置管理 |
| `backend/app/services/catalog_service.py` | 智能体和工作流配置管理 |
| `backend/app/orchestrators/flows/technical_design_flow.py` | 技术设计工作流执行器 |
| `backend/app/orchestrators/flows/delivery_flow.py` | 代码交付工作流执行器 |
| `backend/app/orchestrators/agents/agent_factory.py` | 智能体解析和 prompt 组装 |
| `backend/app/orchestrators/runtime/crewai_stage_runner.py` | CrewAI 调用封装 |

### 20.2 前端关键模块

| 文件或目录 | 说明 |
| --- | --- |
| `frontend/src/main.ts` | 前端应用入口 |
| `frontend/src/router/index.ts` | 路由配置和登录守卫 |
| `frontend/src/layouts/AppShell.vue` | 顶部工作台布局 |
| `frontend/src/views/LoginView.vue` | 登录页 |
| `frontend/src/views/ProjectListView.vue` | 项目空间 |
| `frontend/src/views/ProjectDetailView.vue` | 项目详情 |
| `frontend/src/views/RunMonitorView.vue` | 运行监控 |
| `frontend/src/views/ArtifactCenterView.vue` | 产物中心 |
| `frontend/src/views/LLMConfigView.vue` | 模型配置 |
| `frontend/src/views/AdminConfigView.vue` | 管理配置 |
| `frontend/src/components/AppLogo.vue` | 项目 Logo 组件 |
| `frontend/src/components/StageBoard.vue` | 阶段展示组件 |
| `frontend/src/components/EventTimeline.vue` | 事件时间线 |
| `frontend/src/components/ArtifactGroup.vue` | 产物分组展示 |

## 21. UI 与交互设计说明

当前前端采用“顶部工作台导航 + 内容区仪表盘”的结构，主要考虑：

- 顶部导航比左侧导航更适合当前少量一级入口。
- 项目空间作为首页，降低用户进入系统后的理解成本。
- 运行监控页突出阶段进度、事件时间线和产物状态。
- 产物中心强调集中归档和快速查看。
- Logo 使用“项目核心节点 + 多智能体连接 + 代码括号 + 验证勾”的图形语言，表达项目的多智能体协作、代码交付和验证闭环。

## 22. 部署建议

### 22.1 开发环境

推荐组合：

- SQLite
- Thread 执行模式
- Template 或 Auto 智能体模式
- Vite 开发服务器

优点是启动简单，不依赖 Docker、Redis 和 MySQL。

### 22.2 演示环境

推荐组合：

- SQLite 或 MySQL
- Thread 执行模式
- Template 模式或配置一个可用的 OpenAI 兼容接口
- 前端使用 `pnpm build` 后静态部署

演示环境优先保证稳定性和可重复执行。

### 22.3 正式环境

推荐组合：

- MySQL
- Redis
- Celery Worker
- FastAPI API 服务
- 前端静态资源部署到 Nginx 或对象存储
- HTTPS
- 独立日志与监控

正式环境必须开启：

- 强密钥配置。
- 数据库备份。
- Worker 进程监控。
- 模型调用限流和成本监控。
- 错误日志采集。

## 23. 风险与改进方向

| 风险 | 表现 | 建议 |
| --- | --- | --- |
| 模型输出不稳定 | 输出格式不符合 schema 或内容质量波动 | 加强 guardrails、重试、格式修复和质量评分 |
| 成本不可控 | 多阶段工作流频繁调用模型 | 增加 token 预算、模型分级和调用审计 |
| 工作流灵活性不足 | 当前主要是固定流程 | 后续支持可视化流程编排 |
| 产物版本管理较弱 | 当前 version_no 基础化 | 增加产物版本对比和回滚 |
| 权限体系简单 | 当前更适合单用户或课程场景 | 增加团队、角色和项目成员权限 |
| 测试覆盖不足 | 前端和 Celery 场景仍需补充 | 增加端到端测试和队列模式集成测试 |
| 交付自动化不足 | 目前不直接提交代码仓库 | 后续接入 Git 仓库和 CI 流水线 |

## 24. 后续迭代路线

### 24.1 第二阶段建议

- 增加可视化工作流配置页面。
- 增加产物版本对比能力。
- 增加 PDF 导出。
- 增加前端 E2E 测试。
- 增加运行失败后的阶段级重试。
- 增加模型调用成本统计。

### 24.2 第三阶段建议

- 接入 Git 仓库，支持生成代码分支。
- 接入 CI，对代码交付包自动运行测试。
- 增加团队协作和项目成员权限。
- 增加人工审核节点。
- 增加需求变更影响分析。
- 增加知识库和历史项目复用能力。

### 24.3 长期方向

- 从固定流程升级为可编排的软件工程智能体平台。
- 从文档生成升级为需求、设计、代码、测试、部署全链路协同。
- 从单次运行升级为可持续迭代的项目智能工作台。

## 25. 项目总结

SE-Agent Studio 当前已经具备一个完整软件工程多智能体协作平台的基础形态。它以项目为中心，以工作流为主线，以智能体为执行角色，以运行事件和阶段产物为过程证据，形成了从需求到设计、测试和交付归档的闭环。

从工程实现看，项目采用前后端分离架构，后端用 FastAPI 负责 API、鉴权、数据库和工作流编排，前端用 Vue 3 构建工作台体验。系统既支持轻量的本地线程模式，也预留了 Redis、Celery、MySQL 的正式部署路径；既支持真实 CrewAI 模型调用，也支持模板模式兜底，便于开发、演示和课程验收。

从项目管理看，该项目可以作为软件工程课程中“需求、设计、实现、测试、交付”全流程协作的展示平台，也可以作为后续多智能体软件开发工具的原型基础。
