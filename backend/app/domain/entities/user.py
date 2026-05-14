from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.exceptions import InvariantViolation
from app.domain.value_objects.phone import Phone


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    REJECTED = "rejected"


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class User:
    id: uuid.UUID
    phone: Phone
    password_hash: str
    full_name: str | None = None
    status: UserStatus = UserStatus.PENDING
    role: UserRole = UserRole.USER
    phone_verified: bool = False
    last_login_at: datetime | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    @classmethod
    def register(
        cls,
        *,
        phone: Phone,
        password_hash: str,
        full_name: str | None = None,
    ) -> "User":
        return cls(
            id=uuid.uuid4(),
            phone=phone,
            password_hash=password_hash,
            full_name=full_name,
        )

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def is_blocked(self) -> bool:
        return self.status == UserStatus.BLOCKED

    def mark_phone_verified(self) -> None:
        self.phone_verified = True
        self.updated_at = _utcnow()

    def record_login(self) -> None:
        if self.status != UserStatus.ACTIVE:
            raise InvariantViolation(
                "User account is not active",
                details={"status": self.status.value},
            )
        self.last_login_at = _utcnow()
        self.updated_at = _utcnow()
