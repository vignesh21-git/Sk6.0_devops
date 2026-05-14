from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import SessionFactory


class UnitOfWork:
    """Async context manager that owns a session and commits on success."""

    session: AsyncSession

    async def __aenter__(self) -> "UnitOfWork":
        self.session = SessionFactory()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                await self.session.commit()
            else:
                await self.session.rollback()
        finally:
            await self.session.close()
