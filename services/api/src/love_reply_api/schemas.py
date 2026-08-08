from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


def _to_lower_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=_to_lower_camel, populate_by_name=True)


class SuccessEnvelope(ApiModel, Generic[DataT]):
    code: str = "OK"
    message: str = "success"
    data: DataT
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HealthData(ApiModel):
    status: str
    version: str
