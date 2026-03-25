from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.orchestrators.agents.template_loader import AgentTemplateFile
from app.repositories.catalog_repository import CatalogRepository


@dataclass
class ResolvedAgentProfile:
    agent_code: str
    display_name: str
    description: str
    model: str
    temperature: float
    allow_delegation: bool
    prompt_snapshot: Dict[str, Any]


class AgentFactory:
    def __init__(self, db: Session):
        self.db = db
        self.catalog_repo = CatalogRepository(db)

    def resolve(self, agent_code: str, task_description: str, context: Optional[Dict[str, Any]] = None) -> ResolvedAgentProfile:
        agent = self.catalog_repo.get_agent_by_code(agent_code)
        if not agent:
            raise ValueError("Unknown agent code: %s" % agent_code)

        latest_prompt = self.catalog_repo.latest_prompt_version(agent)
        prompt_snapshot = {
            "system_rules": [
                "All key outputs must be structured and reusable.",
                "Stay within the software engineering workflow boundary.",
            ],
            "backstory": latest_prompt.backstory_prompt if latest_prompt else "",
            "task_description": task_description,
            "context": context or {},
            "rules": latest_prompt.rules_prompt if latest_prompt else "",
        }
        return ResolvedAgentProfile(
            agent_code=agent.agent_code,
            display_name=agent.display_name,
            description=agent.description,
            model=agent.default_model,
            temperature=agent.temperature,
            allow_delegation=agent.allow_delegation,
            prompt_snapshot=prompt_snapshot,
        )

    def maybe_build_crewai_agent(self, agent_code: str, task_description: str, context: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        try:
            from crewai import Agent  # type: ignore
        except ImportError:
            return None

        resolved = self.resolve(agent_code=agent_code, task_description=task_description, context=context)
        return Agent(
            role=resolved.display_name,
            goal=task_description,
            backstory=resolved.prompt_snapshot.get("backstory", ""),
            allow_delegation=resolved.allow_delegation,
            llm=resolved.model or None,
        )
