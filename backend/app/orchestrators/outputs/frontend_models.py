from typing import List

from pydantic import BaseModel


class PageSpec(BaseModel):
    page_name: str
    goal: str
    key_sections: List[str]


class FrontendBlueprint(BaseModel):
    page_tree: List[PageSpec]
    component_map: List[str]
    state_slices: List[str]
    api_bindings: List[str]
    realtime_strategy: List[str]
