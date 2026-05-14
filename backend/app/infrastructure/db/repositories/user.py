from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositories import UserRepository
from app.domain.entities.user import User, UserRole, UserStatus
from app.domain.value_objects.phone import Phone
from app.infrastructure.db.models.user import UserModel


def _to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        phone=Phone(row.phone),
        password_hash=row.password_hash,
        full_name=row.full_name,
        status=UserStatus(row.status),
        role=UserRole(row.role),
        phone_verified=row.phone_verified,
        last_login_at=row.last_login_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        row = await self._session.get(UserModel, user_id)
        return _to_entity(row) if row else None

    async def get_by_phone(self, phone: Phone) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.phone == phone.value)
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def add(self, user: User) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                phone=user.phone.value,
                password_hash=user.password_hash,
                full_name=user.full_name,
                status=user.status.value,
                role=user.role.value,
                phone_verified=user.phone_verified,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
        )
        await self._session.flush()

    async def update(self, user: User) -> None:
        row = await self._session.get(UserModel, user.id)
        if row is None:
            return
        row.phone = user.phone.value
        row.password_hash = user.password_hash
        row.full_name = user.full_name
        row.status = user.status.value
        row.role = user.role.value
        row.phone_verified = user.phone_verified
        row.last_login_at = user.last_login_at
        await self._session.flush()
