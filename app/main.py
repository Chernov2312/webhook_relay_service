import logging

from fastapi import FastAPI, HTTPException
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.db.session import engine

logging.basicConfig(level=settings.log_level.upper())
app = FastAPI(title=settings.app_name, version="1.0.0")
app.include_router(v1_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        try:
            client.ping()
        finally:
            client.close()
    except (SQLAlchemyError, RedisError, OSError, ConnectionError) as exc:
        raise HTTPException(status_code=503, detail="Dependency unavailable") from exc
    return {"status": "ok"}
