from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from app.domain.entities.user import User
from app.domain.value_objects.phone import Phone


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_phone(self, phone: Phone) -> User | None: ...

    @abstractmethod
    async def add(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...
