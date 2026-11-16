from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.endpoint import Endpoint
from app.db.models.event import Event, EventStatus
from app.db.session import get_session
from app.schemas.events import EventAccepted, EventCreate, EventRead
from app.worker.tasks import deliver_webhook

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_event(
    body: EventCreate, session: AsyncSession = Depends(get_session)
) -> EventAccepted:
    endpoint = await session.get(Endpoint, body.endpoint_id)
    if endpoint is None or not endpoint.is_active:
        raise HTTPException(status_code=404, detail="Active endpoint not found")

    event = Event(
        endpoint_id=endpoint.id,
        event_type=body.event_type,
        payload=body.payload,
        status=EventStatus.PENDING,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    deliver_webhook.delay(str(event.id))
    return EventAccepted(event_id=event.id, status=event.status)


@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: UUID, session: AsyncSession = Depends(get_session)
) -> EventRead:
    result = await session.execute(
        select(Event).where(Event.id == event_id).options(selectinload(Event.attempts))
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventRead.model_validate(event)
