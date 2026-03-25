from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.core.config import settings
from app.orchestrators.agents.agent_factory import ResolvedAgentProfile


@dataclass
class CrewAIStageRunResult:
    payload: dict[str, Any]
    raw_output: str
    prompt_tokens: int
    completion_tokens: int


class CrewAIStageRunner:
    def __init__(self, runtime_dir: Path | None = None):
        self.runtime_dir = runtime_dir or settings.runtime_dir

    def run_stage(
        self,
        *,
        crew_name: str,
        agent_profile: ResolvedAgentProfile,
        task_description: str,
        expected_output: str,
        output_model: type[BaseModel],
    ) -> CrewAIStageRunResult:
        self._prepare_environment()

        from crewai import Agent, Crew, LLM, Process, Task  # type: ignore

        llm = self._build_llm(LLM, agent_profile)
        agent = Agent(
            role=agent_profile.display_name,
            goal=task_description,
            backstory=self._compose_backstory(agent_profile),
            allow_delegation=agent_profile.allow_delegation,
            llm=llm,
            verbose=False,
        )
        task = Task(
            name=crew_name,
            description=task_description,
            expected_output=expected_output,
            output_pydantic=output_model,
            agent=agent,
            markdown=False,
        )
        crew = Crew(
            name=crew_name,
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            cache=False,
            memory=False,
            verbose=False,
        )
        crew_output = crew.kickoff()

        payload = self._extract_payload(crew_output, output_model)
        token_usage = getattr(crew_output, "token_usage", None)
        return CrewAIStageRunResult(
            payload=payload,
            raw_output=getattr(crew_output, "raw", "") or "",
            prompt_tokens=getattr(token_usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(token_usage, "completion_tokens", 0) or 0,
        )

    def _prepare_environment(self) -> None:
        crewai_home = self.runtime_dir / "crewai-home"
        crewai_home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(crewai_home)
        os.environ.setdefault("CREWAI_STORAGE_DIR", "se-agent-studio")

    def _build_llm(self, llm_cls: type[Any], agent_profile: ResolvedAgentProfile) -> Any:
        model = agent_profile.model or settings.default_model
        return llm_cls(
            model=model,
            api_key=settings.openai_api_key or None,
            base_url=settings.openai_base_url or None,
            temperature=agent_profile.temperature,
            timeout=settings.llm_timeout_seconds,
        )

    def _compose_backstory(self, agent_profile: ResolvedAgentProfile) -> str:
        snapshot = agent_profile.prompt_snapshot
        sections: list[str] = []

        if agent_profile.description:
            sections.append(f"Role Summary:\n{agent_profile.description}")
        system_rules = snapshot.get("system_rules") or []
        if system_rules:
            sections.append(
                "System Rules:\n" + "\n".join(f"- {rule}" for rule in system_rules if rule)
            )
        if snapshot.get("backstory"):
            sections.append(str(snapshot["backstory"]).strip())
        if snapshot.get("rules"):
            sections.append(f"Operating Rules:\n{snapshot['rules']}")
        context = snapshot.get("context") or {}
        if context:
            sections.append(
                "Project Context:\n"
                + json.dumps(context, ensure_ascii=False, indent=2)
            )

        return "\n\n".join(section for section in sections if section).strip()

    def _extract_payload(self, crew_output: Any, output_model: type[BaseModel]) -> dict[str, Any]:
        if getattr(crew_output, "pydantic", None):
            return output_model.model_validate(crew_output.pydantic).model_dump(mode="json")

        if getattr(crew_output, "json_dict", None):
            return output_model.model_validate(crew_output.json_dict).model_dump(mode="json")

        task_outputs = getattr(crew_output, "tasks_output", []) or []
        if task_outputs:
            final_output = task_outputs[-1]
            if getattr(final_output, "pydantic", None):
                return output_model.model_validate(final_output.pydantic).model_dump(mode="json")
            if getattr(final_output, "json_dict", None):
                return output_model.model_validate(final_output.json_dict).model_dump(mode="json")
            if getattr(final_output, "raw", None):
                return output_model.model_validate_json(final_output.raw).model_dump(mode="json")

        raise ValueError(f"CrewAI stage did not return a valid {output_model.__name__} payload")
