import redis.asyncio as redis_async

from app.core.config import get_settings

_pool: redis_async.ConnectionPool | None = None


def _get_pool() -> redis_async.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis_async.ConnectionPool.from_url(
            get_settings().redis_url, decode_responses=True
        )
    return _pool


def get_redis() -> redis_async.Redis:
    return redis_async.Redis(connection_pool=_get_pool())


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
