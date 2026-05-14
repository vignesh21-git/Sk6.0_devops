from __future__ import annotations

from dataclasses import dataclass

from app.application.interfaces.repositories import UserRepository
from app.application.interfaces.services import OtpStore
from app.application.use_cases.auth._otp import generate_otp
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.domain.value_objects.phone import Phone
from app.infrastructure.external.otp_gateway import OtpGateway


@dataclass(slots=True)
class RequestOtpInput:
    phone: str


@dataclass(slots=True)
class RequestOtpOutput:
    phone: str
    expires_in_seconds: int


class RequestOtpUseCase:
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

    async def execute(self, data: RequestOtpInput) -> RequestOtpOutput:
        phone = Phone(data.phone)

        user = await self._users.get_by_phone(phone)
        if user is None:
            raise NotFoundError(
                "No account found for this phone number",
                details={"phone": phone.value},
            )

        settings = get_settings()
        code = generate_otp()
        ttl = settings.otp_expiry_minutes * 60
        await self._otp_store.put(
            phone=phone.value, code=code, ttl_seconds=ttl
        )
        await self._otp_gateway.send_otp(phone=phone.value, otp=code)

        return RequestOtpOutput(phone=phone.value, expires_in_seconds=ttl)
