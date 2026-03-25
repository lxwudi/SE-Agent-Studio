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
uv sync --extra ai-runtime --dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
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

后端现在支持三种运行模式，通过 `backend/.env` 中的 `AGENT_RUNTIME_MODE` 控制：

- `auto`：默认模式。有可用模型配置时走真实 CrewAI；没有就自动回退到本地模板运行时。
- `crewai`：强制走真实 CrewAI 运行时。如果没有模型配置会直接报错。
- `template`：强制走本地模板运行时，适合离线演示和纯前后端联调。

模型配置最少需要满足下面之一：

- 配置 `OPENAI_API_KEY`，使用默认 OpenAI 兼容接口
- 或把 `OPENAI_BASE_URL` 指向一个可用的 OpenAI 兼容端点

这样本地没有密钥时仍然可以跑完整闭环，而一旦补上模型配置，后端就会自动切到真实 CrewAI 阶段执行。

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
