from __future__ import annotations

from dataclasses import dataclass

from app.application.interfaces.repositories import UserRepository
from app.application.interfaces.services import OtpStore
from app.core.exceptions import AuthenticationError, NotFoundError
from app.domain.value_objects.phone import Phone

MAX_OTP_ATTEMPTS = 5


@dataclass(slots=True)
class VerifyOtpInput:
    phone: str
    otp: str


@dataclass(slots=True)
class VerifyOtpOutput:
    phone: str
    phone_verified: bool
    status: str


class VerifyOtpUseCase:
    def __init__(
        self, *, users: UserRepository, otp_store: OtpStore
    ) -> None:
        self._users = users
        self._otp_store = otp_store

    async def execute(self, data: VerifyOtpInput) -> VerifyOtpOutput:
        phone = Phone(data.phone)

        user = await self._users.get_by_phone(phone)
        if user is None:
            raise NotFoundError("Phone number not registered")

        record = await self._otp_store.get(phone.value)
        if record is None:
            raise AuthenticationError(
                "OTP expired or not requested",
                details={"code": "OTP_NOT_FOUND"},
            )

        if record.attempts >= MAX_OTP_ATTEMPTS:
            await self._otp_store.delete(phone.value)
            raise AuthenticationError(
                "Too many OTP attempts. Request a new one.",
                details={"code": "OTP_LOCKED"},
            )

        if record.code != data.otp:
            await self._otp_store.increment_attempts(phone.value)
            raise AuthenticationError(
                "Invalid OTP",
                details={"code": "OTP_INVALID"},
            )

        user.mark_phone_verified()
        await self._users.update(user)
        await self._otp_store.delete(phone.value)

        return VerifyOtpOutput(
            phone=phone.value,
            phone_verified=user.phone_verified,
            status=user.status.value,
        )
