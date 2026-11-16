import asyncio
import json
from uuid import UUID

import httpx
from celery import Task
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core.security import sign_payload
from app.db.models.delivery_attempt import DeliveryAttempt
from app.db.models.endpoint import Endpoint
from app.db.models.event import Event, EventStatus
from app.db.session import SessionFactory
from app.worker.celery_app import celery_app

MAX_ATTEMPTS = 3


class AttemptResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status_code: int | None
    response_body: str | None
    error_message: str | None
    retryable: bool
    delivered: bool


async def _send_and_record(event_id: UUID, attempt_number: int) -> AttemptResult | None:
    async with SessionFactory() as session:
        result = await session.execute(
            select(Event).where(Event.id == event_id).with_for_update()
        )
        event = result.scalar_one_or_none()
        if event is None or event.status != EventStatus.PENDING:
            return None
        endpoint = await session.get(Endpoint, event.endpoint_id)
        if endpoint is None or not endpoint.is_active:
            event.status = EventStatus.FAILED
            session.add(
                DeliveryAttempt(
                    event_id=event.id,
                    attempt_number=attempt_number,
                    error_message="Endpoint is missing or inactive",
                )
            )
            await session.commit()
            return AttemptResult(
                status_code=None,
                response_body=None,
                error_message="Endpoint is missing or inactive",
                retryable=False,
                delivered=False,
            )

        body = json.dumps(
            {"id": str(event.id), "event_type": event.event_type, "payload": event.payload},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        status_code: int | None = None
        response_body: str | None = None
        error_message: str | None = None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    endpoint.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": sign_payload(endpoint.secret, body),
                    },
                )
            status_code = response.status_code
            response_body = response.text
            delivered = 200 <= status_code < 300
            retryable = status_code == 429 or status_code >= 500
        except httpx.RequestError as exc:
            error_message = str(exc)[:2048]
            delivered = False
            retryable = True

        session.add(
            DeliveryAttempt(
                event_id=event.id,
                attempt_number=attempt_number,
                status_code=status_code,
                response_body=response_body,
                error_message=error_message,
            )
        )
        if delivered:
            event.status = EventStatus.DELIVERED
        elif not retryable or attempt_number >= MAX_ATTEMPTS:
            event.status = EventStatus.FAILED
        await session.commit()
        return AttemptResult(
            status_code=status_code,
            response_body=response_body,
            error_message=error_message,
            retryable=retryable,
            delivered=delivered,
        )


@celery_app.task(bind=True, name="deliver_webhook", max_retries=MAX_ATTEMPTS - 1)
def deliver_webhook(self: Task, event_id: str) -> None:
    attempt_number = self.request.retries + 1
    result = asyncio.run(_send_and_record(UUID(event_id), attempt_number))
    if result is None or result.delivered or not result.retryable:
        return
    if attempt_number < MAX_ATTEMPTS:
        raise self.retry(countdown=2**attempt_number)
