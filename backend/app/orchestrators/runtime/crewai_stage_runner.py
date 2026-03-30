from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.core.config import settings
from app.orchestrators.agents.agent_factory import ResolvedAgentProfile
from app.services.llm_config_service import RuntimeLLMConfig


@dataclass
class CrewAIStageRunResult:
    payload: dict[str, Any]
    raw_output: str
    prompt_tokens: int
    completion_tokens: int


@dataclass
class ResolvedRuntimeSettings:
    provider_name: str
    base_url: str
    api_key: str
    model: str


class CrewAIStageRunner:
    def __init__(self, runtime_dir: Path | None = None, runtime_config: RuntimeLLMConfig | None = None):
        self.runtime_dir = runtime_dir or settings.runtime_dir
        self.runtime_config = runtime_config

    def resolve_model_name(self, agent_profile: ResolvedAgentProfile) -> str:
        return self.resolve_runtime_settings(agent_profile).model

    def resolve_runtime_settings(self, agent_profile: ResolvedAgentProfile) -> ResolvedRuntimeSettings:
        override = self.runtime_config.agent_overrides.get(agent_profile.agent_code) if self.runtime_config else None
        if override and override.override_enabled:
            return ResolvedRuntimeSettings(
                provider_name=override.provider_name.strip()
                or (self.runtime_config.provider_name.strip() if self.runtime_config else "")
                or "OpenAI Compatible",
                base_url=override.base_url.strip()
                or (self.runtime_config.base_url.strip() if self.runtime_config else "")
                or settings.openai_base_url,
                api_key=override.api_key.strip()
                or (self.runtime_config.api_key.strip() if self.runtime_config else "")
                or settings.openai_api_key,
                model=override.default_model.strip() or self._resolve_account_or_role_model(agent_profile),
            )

        return ResolvedRuntimeSettings(
            provider_name=(self.runtime_config.provider_name.strip() if self.runtime_config else "") or "OpenAI Compatible",
            base_url=(self.runtime_config.base_url.strip() if self.runtime_config else "") or settings.openai_base_url,
            api_key=(self.runtime_config.api_key.strip() if self.runtime_config else "") or settings.openai_api_key,
            model=self._resolve_account_or_role_model(agent_profile),
        )

    def _resolve_account_or_role_model(self, agent_profile: ResolvedAgentProfile) -> str:
        if self.runtime_config:
            role_override = self.runtime_config.agent_model_overrides.get(agent_profile.agent_code, "").strip()
            if role_override:
                return role_override
        if self.runtime_config and self.runtime_config.default_model.strip():
            return self.runtime_config.default_model.strip()
        if agent_profile.model.strip():
            return agent_profile.model.strip()
        return settings.default_model

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
        if self._should_skip_structured_output(agent_profile):
            return self._kickoff_stage(
                crew_name=crew_name,
                agent_profile=agent_profile,
                task_description=task_description,
                expected_output=expected_output,
                output_model=output_model,
                use_structured_output=False,
            )
        try:
            return self._kickoff_stage(
                crew_name=crew_name,
                agent_profile=agent_profile,
                task_description=task_description,
                expected_output=expected_output,
                output_model=output_model,
                use_structured_output=True,
            )
        except Exception as exc:
            if not self._should_retry_without_structured_output(exc):
                raise
            return self._kickoff_stage(
                crew_name=crew_name,
                agent_profile=agent_profile,
                task_description=task_description,
                expected_output=expected_output,
                output_model=output_model,
                use_structured_output=False,
            )

    def _kickoff_stage(
        self,
        *,
        crew_name: str,
        agent_profile: ResolvedAgentProfile,
        task_description: str,
        expected_output: str,
        output_model: type[BaseModel],
        use_structured_output: bool,
    ) -> CrewAIStageRunResult:
        description, expected = self._build_task_contract(
            task_description=task_description,
            expected_output=expected_output,
            output_model=output_model,
            use_structured_output=use_structured_output,
        )

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
        task_kwargs: dict[str, Any] = {
            "name": crew_name,
            "description": description,
            "expected_output": expected,
            "agent": agent,
            "markdown": False,
        }
        if use_structured_output:
            task_kwargs["output_pydantic"] = output_model
        task = Task(**task_kwargs)
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

        payload = self._extract_payload(crew_output, output_model, prefer_raw=not use_structured_output)
        token_usage = getattr(crew_output, "token_usage", None)
        return CrewAIStageRunResult(
            payload=payload,
            raw_output=getattr(crew_output, "raw", "") or "",
            prompt_tokens=getattr(token_usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(token_usage, "completion_tokens", 0) or 0,
        )

    def _build_task_contract(
        self,
        *,
        task_description: str,
        expected_output: str,
        output_model: type[BaseModel],
        use_structured_output: bool,
    ) -> tuple[str, str]:
        if use_structured_output:
            return task_description, expected_output

        schema_text = json.dumps(output_model.model_json_schema(), ensure_ascii=False, indent=2)
        description = (
            f"{task_description}\n\n"
            "Output contract:\n"
            "- Return exactly one JSON object.\n"
            "- Do not wrap the JSON with markdown code fences.\n"
            "- Do not add explanations before or after the JSON.\n"
            "- The JSON must satisfy this schema:\n"
            f"{schema_text}"
        )
        expected = (
            f"{expected_output}\n"
            "Return only one valid JSON object that matches the schema exactly."
        )
        return description, expected

    def _should_retry_without_structured_output(self, exc: Exception) -> bool:
        message = str(exc).lower()
        markers = (
            "response_format",
            "json_schema",
            "structured output",
            "response format",
        )
        return any(marker in message for marker in markers)

    def _should_skip_structured_output(self, agent_profile: ResolvedAgentProfile) -> bool:
        runtime = self.resolve_runtime_settings(agent_profile)
        provider_name = runtime.provider_name.lower()
        base_url = runtime.base_url.lower()
        model_name = runtime.model.lower()
        hints = (provider_name, base_url, model_name)
        return any("deepseek" in hint for hint in hints if hint)

    def _prepare_environment(self) -> None:
        crewai_home = self.runtime_dir / "crewai-home"
        crewai_home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(crewai_home)
        os.environ.setdefault("CREWAI_STORAGE_DIR", "se-agent-studio")

    def _build_llm(self, llm_cls: type[Any], agent_profile: ResolvedAgentProfile) -> Any:
        runtime = self.resolve_runtime_settings(agent_profile)
        return llm_cls(
            model=runtime.model,
            api_key=runtime.api_key or None,
            base_url=runtime.base_url or None,
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

        return "\n\n".join(section for section in sections if section).strip()

    def _extract_payload(
        self,
        crew_output: Any,
        output_model: type[BaseModel],
        *,
        prefer_raw: bool = False,
    ) -> dict[str, Any]:
        if prefer_raw:
            raw_payload = self._extract_payload_from_raw_outputs(crew_output, output_model)
            if raw_payload is not None:
                return raw_payload

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
                return self._extract_payload_from_text(final_output.raw, output_model)

        if not prefer_raw:
            raw_payload = self._extract_payload_from_raw_outputs(crew_output, output_model)
            if raw_payload is not None:
                return raw_payload

        raise ValueError(f"CrewAI stage did not return a valid {output_model.__name__} payload")

    def _extract_payload_from_raw_outputs(
        self,
        crew_output: Any,
        output_model: type[BaseModel],
    ) -> dict[str, Any] | None:
        raw_output = getattr(crew_output, "raw", None)
        if raw_output:
            return self._extract_payload_from_text(raw_output, output_model)

        task_outputs = getattr(crew_output, "tasks_output", []) or []
        for task_output in reversed(task_outputs):
            if getattr(task_output, "raw", None):
                return self._extract_payload_from_text(task_output.raw, output_model)
        return None

    def _extract_payload_from_text(self, text: str, output_model: type[BaseModel]) -> dict[str, Any]:
        candidate = self._extract_json_object(text)
        return output_model.model_validate_json(candidate).model_dump(mode="json")

    def _extract_json_object(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("CrewAI raw output is empty.")

        fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
        for block in fenced_blocks:
            block_cleaned = block.strip()
            if block_cleaned.startswith("{") and block_cleaned.endswith("}"):
                return block_cleaned

        if cleaned.startswith("{") and cleaned.endswith("}"):
            return cleaned

        object_start = cleaned.find("{")
        object_end = cleaned.rfind("}")
        if object_start != -1 and object_end != -1 and object_end > object_start:
            return cleaned[object_start : object_end + 1]

        raise ValueError("CrewAI raw output does not contain a JSON object.")
