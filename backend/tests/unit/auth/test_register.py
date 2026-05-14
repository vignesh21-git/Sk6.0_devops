import pytest

from app.application.use_cases.auth.register import (
    RegisterUserInput,
    RegisterUserUseCase,
)
from app.core.exceptions import ConflictError, InvariantViolation

from tests.unit.fakes.otp_gateway import FakeOtpGateway
from tests.unit.fakes.stores import FakeOtpStore
from tests.unit.fakes.user_repository import FakeUserRepository


@pytest.mark.asyncio
async def test_register_creates_pending_user_and_sends_otp():
    users = FakeUserRepository()
    otp_store = FakeOtpStore()
    gateway = FakeOtpGateway()

    out = await RegisterUserUseCase(
        users=users, otp_store=otp_store, otp_gateway=gateway
    ).execute(
        RegisterUserInput(
            phone="9876543210", password="secret123", full_name="Test User"
        )
    )

    assert out.phone == "9876543210"
    assert out.status == "pending"
    assert out.phone_verified is False
    assert len(users.by_phone) == 1
    assert otp_store.codes["9876543210"]
    assert gateway.sent == [("9876543210", otp_store.codes["9876543210"])]


@pytest.mark.asyncio
async def test_register_rejects_duplicate_phone():
    users = FakeUserRepository()
    otp_store = FakeOtpStore()
    gateway = FakeOtpGateway()
    uc = RegisterUserUseCase(
        users=users, otp_store=otp_store, otp_gateway=gateway
    )
    await uc.execute(
        RegisterUserInput(phone="9876543210", password="secret123")
    )

    with pytest.raises(ConflictError):
        await uc.execute(
            RegisterUserInput(phone="9876543210", password="other123")
        )


@pytest.mark.asyncio
async def test_register_normalizes_indian_phone_with_country_code():
    users = FakeUserRepository()
    out = await RegisterUserUseCase(
        users=users, otp_store=FakeOtpStore(), otp_gateway=FakeOtpGateway()
    ).execute(
        RegisterUserInput(phone="+919876543210", password="secret123")
    )
    assert out.phone == "9876543210"


@pytest.mark.asyncio
async def test_register_rejects_invalid_phone():
    with pytest.raises(InvariantViolation):
        await RegisterUserUseCase(
            users=FakeUserRepository(),
            otp_store=FakeOtpStore(),
            otp_gateway=FakeOtpGateway(),
        ).execute(RegisterUserInput(phone="12345", password="secret123"))
