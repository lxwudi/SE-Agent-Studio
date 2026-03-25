from typing import List

from pydantic import BaseModel


class EntityDefinition(BaseModel):
    name: str
    purpose: str
    key_fields: List[str]


class ApiEndpointContract(BaseModel):
    method: str
    path: str
    summary: str
    request_shape: str
    response_shape: str


class BackendDesign(BaseModel):
    service_boundary: List[str]
    entities: List[EntityDefinition]
    api_contracts: List[ApiEndpointContract]
    async_strategy: List[str]
    observability: List[str]
    risks: List[str]
