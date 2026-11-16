from fastapi import APIRouter

from app.api.v1 import endpoints, events

router = APIRouter(prefix="/api/v1")
router.include_router(endpoints.router)
router.include_router(events.router)
