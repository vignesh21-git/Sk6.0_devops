from __future__ import annotations

from dataclasses import dataclass

from app.application.interfaces.repositories import UserRepository
from app.application.interfaces.services import OtpStore
from app.application.use_cases.auth._otp import generate_otp
from app.core.config import get_settings
from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.domain.entities.user import User
from app.domain.value_objects.phone import Phone
from app.infrastructure.external.otp_gateway import OtpGateway


@dataclass(slots=True)
class RegisterUserInput:
    phone: str
    password: str
    full_name: str | None = None


@dataclass(slots=True)
class RegisterUserOutput:
    user_id: str
    phone: str
    status: str
    phone_verified: bool


class RegisterUserUseCase:
    def __init__(
        self,
        *,
        users: UserRepository,
        otp_store: OtpStore,
        otp_gateway: OtpGateway,
    ) -> None:
        self._users = users
        self._otp_store = otp_store
        self._otp_gateway = otp_gateway

    async def execute(self, data: RegisterUserInput) -> RegisterUserOutput:
        phone = Phone(data.phone)

        existing = await self._users.get_by_phone(phone)
        if existing is not None:
            raise ConflictError(
                "Phone number already registered",
                details={"phone": phone.value},
            )

        user = User.register(
            phone=phone,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
        )
        await self._users.add(user)

        settings = get_settings()
        code = generate_otp()
        await self._otp_store.put(
            phone=phone.value,
            code=code,
            ttl_seconds=settings.otp_expiry_minutes * 60,
        )
        await self._otp_gateway.send_otp(phone=phone.value, otp=code)

        return RegisterUserOutput(
            user_id=str(user.id),
            phone=phone.value,
            status=user.status.value,
            phone_verified=user.phone_verified,
        )
