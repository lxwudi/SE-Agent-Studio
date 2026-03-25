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

    workflow_stmt = select(WorkflowTemplate).where(WorkflowTemplate.workflow_code == "technical_design_v1")
    workflow = db.scalar(workflow_stmt)
    if not workflow:
        workflow = WorkflowTemplate(
            workflow_code="technical_design_v1",
            name="技术设计固定流程 V1",
            description="需求结构化 -> 架构 -> 后端/前端/AI -> 测试 -> 一致性评审",
            version=1,
            enabled=True,
            config_json={"supports_review": False, "supports_parallel_hint": True},
        )
        db.add(workflow)
        db.flush()

        steps = [
            ("requirements", "crew", "product_manager", [], None, "RequirementSpec", 10),
            ("architecture", "crew", "software_architect", ["requirements"], None, "ArchitectureBlueprint", 20),
            ("backend_design", "crew", "backend_architect", ["architecture"], "design", "BackendDesign", 30),
            ("frontend_design", "crew", "frontend_developer", ["architecture"], "design", "FrontendBlueprint", 40),
            ("ai_design", "crew", "ai_engineer", ["architecture"], "design", "AIIntegrationSpec", 50),
            ("quality_assurance", "crew", "api_tester", ["backend_design", "frontend_design", "ai_design"], None, "ApiTestPlan", 60),
            ("consistency_review", "crew", "software_architect", ["quality_assurance"], None, "ConsistencyReviewSummary", 70),
        ]
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

    db.commit()


class BootstrapService:
    @staticmethod
    def bootstrap(session: Session) -> None:
        bootstrap_catalog(session)

    @staticmethod
    def seed_defaults(session: Session) -> None:
        bootstrap_catalog(session)
