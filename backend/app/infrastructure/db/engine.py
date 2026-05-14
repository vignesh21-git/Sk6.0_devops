from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings


def _create_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        # PgBouncer runs in transaction-pool mode. Prepared-statement caches
        # leak between sessions and break — disable both layers.
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )


engine: AsyncEngine = _create_engine()
