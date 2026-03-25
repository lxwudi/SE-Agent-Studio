import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict


class ArtifactListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    artifact_uid: str
    artifact_type: str
    title: str
    version_no: int
    created_at: dt.datetime


class ArtifactDetail(ArtifactListItem):
    content_markdown: str
    content_json: dict[str, Any]


class ArtifactResponse(ArtifactListItem):
    pass


class ArtifactDetailResponse(ArtifactDetail):
    pass
