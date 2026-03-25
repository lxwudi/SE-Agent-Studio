from typing import List

from pydantic import BaseModel


class ADRItem(BaseModel):
    title: str
    decision: str
    rationale: str
    trade_off: str


class ArchitectureBlueprint(BaseModel):
    architecture_style: str
    core_modules: List[str]
    data_flow: List[str]
    deployment_units: List[str]
    key_decisions: List[str]
    risks: List[str]
    adrs: List[ADRItem]
