from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.application.interfaces.repositories import UserRepository
from app.application.interfaces.services import SessionRecord, SessionStore
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import create_access_token, verify_password
from app.domain.entities.user import UserStatus
from app.domain.value_objects.phone import Phone


@dataclass(slots=True)
class LoginInput:
    phone: str
    password: str


@dataclass(slots=True)
class LoginOutput:
    access_token: str
    token_type: str
    expires_in: int
    user_id: str
    role: str


class LoginUseCase:
    def __init__(
        self, *, users: UserRepository, sessions: SessionStore
    ) -> None:
        self._users = users
        self._sessions = sessions

    async def execute(self, data: LoginInput) -> LoginOutput:
        phone = Phone(data.phone)
        user = await self._users.get_by_phone(phone)

        if user is None or not verify_password(data.password, user.password_hash):
            raise AuthenticationError("Invalid phone or password")

        if not user.phone_verified:
            raise AuthorizationError(
                "Phone number not verified. Complete OTP verification first.",
                details={"code": "PHONE_NOT_VERIFIED"},
            )

        if user.status == UserStatus.PENDING:
            raise AuthorizationError(
                "Account pending admin approval",
                details={"code": "USER_PENDING_APPROVAL"},
            )
        if user.status == UserStatus.BLOCKED:
            raise AuthorizationError(
                "Account is blocked",
                details={"code": "USER_BLOCKED"},
            )
        if user.status == UserStatus.REJECTED:
            raise AuthorizationError(
                "Account has been rejected",
                details={"code": "USER_REJECTED"},
            )

        user.record_login()
        await self._users.update(user)

        token, jti, expires_at = create_access_token(
            user_id=str(user.id), role=user.role.value
        )
        ttl_seconds = int(
            (expires_at - datetime.now(timezone.utc)).total_seconds()
        )
        await self._sessions.put(
            jti=jti,
            record=SessionRecord(
                user_id=user.id,
                role=user.role.value,
                issued_at=datetime.now(timezone.utc),
            ),
            ttl_seconds=ttl_seconds,
        )

        settings = get_settings()
        return LoginOutput(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_expire_hours * 3600,
            user_id=str(user.id),
            role=user.role.value,
        )
