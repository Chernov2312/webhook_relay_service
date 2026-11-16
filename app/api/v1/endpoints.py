from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_secret
from app.db.models.endpoint import Endpoint
from app.db.session import get_session
from app.schemas.endpoints import EndpointCreate, EndpointCreated, EndpointRead

router = APIRouter(prefix="/endpoints", tags=["endpoints"])


@router.post("", response_model=EndpointCreated, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    body: EndpointCreate, session: AsyncSession = Depends(get_session)
) -> Endpoint:
    endpoint = Endpoint(url=str(body.url), secret=generate_secret())
    session.add(endpoint)
    await session.commit()
    await session.refresh(endpoint)
    return endpoint


@router.get("/{endpoint_id}", response_model=EndpointRead)
async def get_endpoint(endpoint_id: UUID, session: AsyncSession = Depends(get_session)) -> Endpoint:
    endpoint = await session.get(Endpoint, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return endpoint
