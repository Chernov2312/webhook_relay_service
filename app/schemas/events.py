from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.event import EventStatus


class EventCreate(BaseModel):
    endpoint_id: UUID
    event_type: str = Field(min_length=1, max_length=255)
    payload: dict


class EventAccepted(BaseModel):
    event_id: UUID
    status: EventStatus


class DeliveryAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_number: int
    status_code: int | None
    response_body: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    endpoint_id: UUID
    event_type: str
    payload: dict
    status: EventStatus
    created_at: datetime
    updated_at: datetime
    delivery_attempts: list[DeliveryAttemptRead] = Field(validation_alias="attempts")
