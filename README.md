# SE-Agent Studio

根据《SE-Agent Studio 开发前技术设计文档》推进的可运行第一版。

当前仓库拆成两部分：

- `backend/`: 基于 `uv` 管理的 FastAPI 后端
- `frontend/`: 基于 `pnpm` 管理的 Vue 3 前端

## 推荐启动顺序

```bash
docker compose up -d mysql redis
```

```bash
cd backend
cp .env.example .env
uv sync --extra ai-runtime --extra dev
uv run alembic upgrade head
uv run python scripts/bootstrap_data.py
uv run uvicorn app.main:app --reload
```

```bash
cd backend
uv run celery -A app.workers.celery_app:celery_app worker --loglevel=info
```

```bash
cd frontend
pnpm install
pnpm dev
```

## 默认登录账号

- 邮箱：`demo@se-agent.studio`
- 密码：`ChangeMe123!`

以上默认值来自 `backend/.env` 中的 `DEFAULT_OWNER_EMAIL` 和 `DEFAULT_OWNER_PASSWORD`，正式部署前请务必修改。

## 用户自助配置模型 API

现在登录用户可以在产品内自己配置云端模型接口，而不是只能靠服务端 `.env`：

- 页面入口：`/settings/llm`
- 支持方式：任何兼容 `OpenAI API` 的云端接口
- 可配置项：服务名称、`base_url`、默认模型、API Key、启用状态

运行时优先级：

1. 用户自己在产品内保存并启用的 API 配置
2. 服务端 `.env` 中的 `OPENAI_API_KEY / OPENAI_BASE_URL`
3. 如果都没有，再按 `AGENT_RUNTIME_MODE` 决定是否回退到模板模式

生产环境建议额外设置 `SECRET_ENCRYPTION_KEY`，用于加密数据库里的用户 API Key；如果不设置，系统会退回到基于 `JWT_SECRET` 派生的加密 key。

## 启动边界

应用启动默认不会自动建表，也不会自动写入默认用户 / workflow / agent 数据。

- 数据库 schema：通过 `uv run alembic upgrade head` 显式执行
- 默认数据 bootstrap：通过 `uv run python scripts/bootstrap_data.py` 显式执行
- 只有在你手动设置 `AUTO_CREATE_SCHEMA=true` 或 `BOOTSTRAP_DATA_ON_STARTUP=true` 时，应用启动才会执行这些动作

这让开发、测试和正式部署的职责边界更清楚，也避免 Web 进程在启动时偷偷改库。

## 当前已落地范围

- 登录鉴权与受保护路由
- 项目管理 API
- 固定工作流运行 API
- 运行事件与产物中心 API
- 角色模板同步到数据库
- Alembic 初始迁移
- CrewAI 真实运行时接入，保留模板兜底
- 前端登录页 / 项目页 / 运行监控页 / 产物中心 / 管理配置页
- 后端 smoke test 用例

## 当前实现说明

后端现在支持三种 Agent 运行模式，通过 `backend/.env` 中的 `AGENT_RUNTIME_MODE` 控制：

- `auto`：默认模式。有可用模型配置时走真实 CrewAI；没有就自动回退到本地模板运行时。
- `crewai`：强制走真实 CrewAI 运行时。如果没有模型配置会直接报错。
- `template`：强制走本地模板运行时，适合离线演示和纯前后端联调。

模型配置最少需要满足下面之一：

- 配置 `OPENAI_API_KEY`，使用默认 OpenAI 兼容接口
- 或把 `OPENAI_BASE_URL` 指向一个可用的 OpenAI 兼容端点

这样本地没有密钥时仍然可以跑完整闭环，而一旦补上模型配置，后端就会自动切到真实 CrewAI 阶段执行。

## 执行模式

正式部署默认使用 `EXECUTION_MODE=celery`，运行创建后会把任务投递给独立 Worker：

- Web API：负责鉴权、创建项目、创建运行、查询状态
- Celery Worker：负责真正执行多阶段 Flow
- Redis：作为 Broker / Result Backend

如果你只是想在本地快速单进程演示，可以显式改成：

```bash
EXECUTION_MODE=thread
```

线程模式只建议用于开发调试；正式环境请保持 `celery`，并确保 `uvicorn` 与 `celery worker` 同时运行。

## 自动化验证

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
