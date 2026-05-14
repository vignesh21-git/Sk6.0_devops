from __future__ import annotations

import uuid

from app.application.interfaces.repositories import UserRepository
from app.domain.entities.user import User
from app.domain.value_objects.phone import Phone


class FakeUserRepository(UserRepository):
    def __init__(self) -> None:
        self.by_id: dict[uuid.UUID, User] = {}
        self.by_phone: dict[str, User] = {}

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.by_id.get(user_id)

    async def get_by_phone(self, phone: Phone) -> User | None:
        return self.by_phone.get(phone.value)

    async def add(self, user: User) -> None:
        self.by_id[user.id] = user
        self.by_phone[user.phone.value] = user

    async def update(self, user: User) -> None:
        self.by_id[user.id] = user
        self.by_phone[user.phone.value] = user
