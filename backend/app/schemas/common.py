from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

