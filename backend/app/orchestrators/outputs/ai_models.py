from typing import List

from pydantic import BaseModel


class AIIntegrationSpec(BaseModel):
    provider_strategy: List[str]
    model_policy: List[str]
    prompt_policy: List[str]
    output_schemas: List[str]
    evaluation_plan: List[str]
    guardrails: List[str]
