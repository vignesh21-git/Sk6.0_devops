from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class SessionRecord:
    user_id: uuid.UUID
    role: str
    issued_at: datetime


class SessionStore(ABC):
    """Tracks active JWT sessions by jti. Fast revocation on block/logout."""

    @abstractmethod
    async def put(
        self, *, jti: str, record: SessionRecord, ttl_seconds: int
    ) -> None: ...

    @abstractmethod
    async def get(self, jti: str) -> SessionRecord | None: ...

    @abstractmethod
    async def revoke(self, jti: str) -> None: ...

    @abstractmethod
    async def revoke_user_sessions(self, user_id: uuid.UUID) -> int:
        """Revoke every active session for the given user. Returns count."""
        ...


@dataclass(slots=True)
class OtpRecord:
    code: str
    attempts: int


class OtpStore(ABC):
    """Stores active OTP challenges keyed by phone, with TTL + attempt counter."""

    @abstractmethod
    async def put(
        self, *, phone: str, code: str, ttl_seconds: int
    ) -> None: ...

    @abstractmethod
    async def get(self, phone: str) -> OtpRecord | None: ...

    @abstractmethod
    async def increment_attempts(self, phone: str) -> int: ...

    @abstractmethod
    async def delete(self, phone: str) -> None: ...
