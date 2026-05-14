import pytest

from app.application.use_cases.auth.register import (
    RegisterUserInput,
    RegisterUserUseCase,
)
from app.application.use_cases.auth.verify_otp import (
    VerifyOtpInput,
    VerifyOtpUseCase,
)
from app.core.exceptions import AuthenticationError

from tests.unit.fakes.otp_gateway import FakeOtpGateway
from tests.unit.fakes.stores import FakeOtpStore
from tests.unit.fakes.user_repository import FakeUserRepository


async def _register(users, otp_store, gateway, phone="9876543210"):
    await RegisterUserUseCase(
        users=users, otp_store=otp_store, otp_gateway=gateway
    ).execute(RegisterUserInput(phone=phone, password="secret123"))


@pytest.mark.asyncio
async def test_verify_otp_marks_phone_verified():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await _register(users, otp_store, gateway)
    code = otp_store.codes["9876543210"]

    out = await VerifyOtpUseCase(users=users, otp_store=otp_store).execute(
        VerifyOtpInput(phone="9876543210", otp=code)
    )

    assert out.phone_verified is True
    assert out.status == "pending"  # admin approval still required
    assert "9876543210" not in otp_store.codes  # OTP consumed


@pytest.mark.asyncio
async def test_verify_otp_rejects_wrong_code_and_counts_attempt():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await _register(users, otp_store, gateway)

    with pytest.raises(AuthenticationError):
        await VerifyOtpUseCase(users=users, otp_store=otp_store).execute(
            VerifyOtpInput(phone="9876543210", otp="000000")
        )
    assert otp_store.attempts["9876543210"] == 1


@pytest.mark.asyncio
async def test_verify_otp_locks_after_max_attempts():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await _register(users, otp_store, gateway)

    # Burn 5 attempts.
    for _ in range(5):
        with pytest.raises(AuthenticationError):
            await VerifyOtpUseCase(users=users, otp_store=otp_store).execute(
                VerifyOtpInput(phone="9876543210", otp="000000")
            )
    # 6th: even with the right code, must fail with OTP_LOCKED and clear it.
    code = otp_store.codes["9876543210"]
    with pytest.raises(AuthenticationError) as exc_info:
        await VerifyOtpUseCase(users=users, otp_store=otp_store).execute(
            VerifyOtpInput(phone="9876543210", otp=code)
        )
    assert exc_info.value.details["code"] == "OTP_LOCKED"
    assert "9876543210" not in otp_store.codes
