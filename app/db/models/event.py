import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON, Uuid

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_attempt import DeliveryAttempt
    from app.db.models.endpoint import Endpoint


class EventStatus(enum.StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class Event(Base):
    __tablename__ = "events"

    endpoint_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("endpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    status: Mapped[EventStatus] = mapped_column(
        Enum(
            EventStatus,
            name="event_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=EventStatus.PENDING,
    )
    endpoint: Mapped["Endpoint"] = relationship(back_populates="events")
    attempts: Mapped[list["DeliveryAttempt"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="DeliveryAttempt.attempt_number",
    )
