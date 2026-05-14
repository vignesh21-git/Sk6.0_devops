from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1 import auth as auth_router
from app.api.v1 import users as users_router
from app.core.config import get_settings
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.infrastructure.cache.redis_client import close_redis, get_redis
from app.infrastructure.db.session import SessionFactory

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    log.info("startup", environment=settings.environment)
    yield
    await close_redis()
    log.info("shutdown")


app = FastAPI(
    title="Sk6.0",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

install_exception_handlers(app)

app.include_router(auth_router.router)
app.include_router(users_router.router)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    result: dict = {
        "status": "ok",
        "environment": settings.environment,
        "db": "unknown",
        "redis": "unknown",
    }

    try:
        async with SessionFactory() as session:
            await session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    try:
        await get_redis().ping()
        result["redis"] = "ok"
    except Exception as e:
        result["redis"] = f"error: {type(e).__name__}"
        result["status"] = "degraded"

    return result
