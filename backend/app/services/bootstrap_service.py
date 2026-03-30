import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import AgentProfile, PromptTemplateVersion, User, WorkflowStep, WorkflowTemplate
from app.orchestrators.agents.template_loader import load_agent_templates


def ensure_default_user(db: Session) -> User:
    stmt = select(User).where(User.email == settings.default_owner_email)
    user = db.scalar(stmt)
    if user:
        if not user.password_hash:
            user.password_hash = hash_password(settings.default_owner_password)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(
        uid=uuid.uuid4().hex,
        email=settings.default_owner_email.lower(),
        display_name=settings.default_owner_name,
        password_hash=hash_password(settings.default_owner_password),
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def bootstrap_catalog(db: Session) -> None:
    ensure_default_user(db)
    templates = load_agent_templates(settings.agents_dir)
    for template in templates:
        stmt = select(AgentProfile).where(AgentProfile.agent_code == template.agent_code)
        agent = db.scalar(stmt)
        if not agent:
            agent = AgentProfile(
                agent_code=template.agent_code,
                display_name=template.display_name,
                description=template.description,
                source_file=template.source_file,
                default_model=settings.default_model,
                temperature=0.2,
                allow_delegation=False,
                enabled=True,
                meta_json={key: value for key, value in template.metadata.items() if key not in {"name", "description"}},
            )
            db.add(agent)
            db.flush()

        prompt_exists = any(item.version == 1 for item in agent.prompt_versions)
        if not prompt_exists:
            db.add(
                PromptTemplateVersion(
                    agent_profile_id=agent.id,
                    version=1,
                    system_prompt="You are part of SE-Agent Studio. Produce stable, structured outputs.",
                    backstory_prompt=template.body,
                    rules_prompt="Stay focused on software engineering deliverables. Avoid placeholder text.",
                )
            )

    ensure_workflow(
        db,
        workflow_code="technical_design_v1",
        name="技术设计固定流程 V1",
        description="需求结构化 -> 架构 -> 后端/前端/AI -> 测试 -> 一致性评审",
        config_json={"supports_review": False, "supports_parallel_hint": True},
        steps=[
            ("requirements", "crew", "product_manager", [], None, "RequirementSpec", 10),
            ("architecture", "crew", "software_architect", ["requirements"], None, "ArchitectureBlueprint", 20),
            ("backend_design", "crew", "backend_architect", ["architecture"], "design", "BackendDesign", 30),
            ("frontend_design", "crew", "frontend_developer", ["architecture"], "design", "FrontendBlueprint", 40),
            ("ai_design", "crew", "ai_engineer", ["architecture"], "design", "AIIntegrationSpec", 50),
            ("quality_assurance", "crew", "api_tester", ["backend_design", "frontend_design", "ai_design"], None, "ApiTestPlan", 60),
            ("consistency_review", "crew", "software_architect", ["quality_assurance"], None, "ConsistencyReviewSummary", 70),
        ],
    )
    ensure_workflow(
        db,
        workflow_code="delivery_v1",
        name="代码交付固定流程 V1",
        description="交付需求 -> 实施方案 -> 后端/前端代码包 -> 集成 -> 交付移交",
        config_json={"supports_review": False, "supports_parallel_hint": True, "delivery_mode": "starter"},
        steps=[
            ("delivery_requirements", "crew", "product_manager", [], None, "DeliveryRequirementSpec", 10),
            ("solution_design", "crew", "software_architect", ["delivery_requirements"], None, "SolutionDeliveryPlan", 20),
            ("backend_delivery", "crew", "backend_architect", ["solution_design"], "delivery", "CodeBundle", 30),
            ("frontend_delivery", "crew", "frontend_developer", ["solution_design"], "delivery", "CodeBundle", 40),
            ("integration", "crew", "api_tester", ["backend_delivery", "frontend_delivery"], None, "IntegrationBundle", 50),
            ("handoff", "crew", "software_architect", ["integration"], None, "DeliveryHandoff", 60),
        ],
    )

    db.commit()


def ensure_workflow(
    db: Session,
    *,
    workflow_code: str,
    name: str,
    description: str,
    config_json: dict,
    steps: list[tuple[str, str, str, list[str], str | None, str, int]],
) -> None:
    workflow_stmt = select(WorkflowTemplate).where(WorkflowTemplate.workflow_code == workflow_code)
    workflow = db.scalar(workflow_stmt)
    if workflow:
        return

    workflow = WorkflowTemplate(
        workflow_code=workflow_code,
        name=name,
        description=description,
        version=1,
        enabled=True,
        config_json=config_json,
    )
    db.add(workflow)
    db.flush()

    for step_code, step_type, agent_code, depends_on, parallel_group, output_schema, sort_order in steps:
        db.add(
            WorkflowStep(
                workflow_template_id=workflow.id,
                step_code=step_code,
                step_type=step_type,
                agent_code=agent_code,
                depends_on=depends_on,
                parallel_group=parallel_group,
                output_schema=output_schema,
                sort_order=sort_order,
            )
        )


class BootstrapService:
    @staticmethod
    def bootstrap(session: Session) -> None:
        bootstrap_catalog(session)

    @staticmethod
    def seed_defaults(session: Session) -> None:
        bootstrap_catalog(session)
