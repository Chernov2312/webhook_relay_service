from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class EndpointCreate(BaseModel):
    url: AnyHttpUrl


class EndpointCreated(BaseModel):
    id: UUID
    url: str
    secret: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EndpointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


