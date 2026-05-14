import pytest

from app.application.use_cases.auth.login import LoginInput, LoginUseCase
from app.application.use_cases.auth.register import (
    RegisterUserInput,
    RegisterUserUseCase,
)
from app.application.use_cases.auth.verify_otp import (
    VerifyOtpInput,
    VerifyOtpUseCase,
)
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.domain.entities.user import UserStatus

from tests.unit.fakes.otp_gateway import FakeOtpGateway
from tests.unit.fakes.stores import FakeOtpStore, FakeSessionStore
from tests.unit.fakes.user_repository import FakeUserRepository


async def _register_and_verify(users, otp_store, gateway, phone="9876543210"):
    await RegisterUserUseCase(
        users=users, otp_store=otp_store, otp_gateway=gateway
    ).execute(RegisterUserInput(phone=phone, password="secret123"))
    code = otp_store.codes[phone]
    await VerifyOtpUseCase(users=users, otp_store=otp_store).execute(
        VerifyOtpInput(phone=phone, otp=code)
    )


@pytest.mark.asyncio
async def test_login_blocks_pending_user():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await _register_and_verify(users, otp_store, gateway)

    with pytest.raises(AuthorizationError) as exc:
        await LoginUseCase(users=users, sessions=FakeSessionStore()).execute(
            LoginInput(phone="9876543210", password="secret123")
        )
    assert exc.value.details["code"] == "USER_PENDING_APPROVAL"


@pytest.mark.asyncio
async def test_login_issues_jwt_for_active_user_and_creates_session():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await _register_and_verify(users, otp_store, gateway)

    # Simulate admin approval.
    user = await users.get_by_phone(
        list(users.by_phone.values())[0].phone
    )
    user.status = UserStatus.ACTIVE
    await users.update(user)

    sessions = FakeSessionStore()
    out = await LoginUseCase(users=users, sessions=sessions).execute(
        LoginInput(phone="9876543210", password="secret123")
    )

    payload = decode_access_token(out.access_token)
    assert payload["sub"] == out.user_id
    assert payload["role"] == "user"
    assert payload["jti"] in sessions.sessions


@pytest.mark.asyncio
async def test_login_rejects_wrong_password():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await _register_and_verify(users, otp_store, gateway)
    user = list(users.by_phone.values())[0]
    user.status = UserStatus.ACTIVE
    await users.update(user)

    with pytest.raises(AuthenticationError):
        await LoginUseCase(users=users, sessions=FakeSessionStore()).execute(
            LoginInput(phone="9876543210", password="wrong-password")
        )


@pytest.mark.asyncio
async def test_login_rejects_unverified_phone():
    users, otp_store, gateway = (
        FakeUserRepository(),
        FakeOtpStore(),
        FakeOtpGateway(),
    )
    await RegisterUserUseCase(
        users=users, otp_store=otp_store, otp_gateway=gateway
    ).execute(
        RegisterUserInput(phone="9876543210", password="secret123")
    )
    # Phone NOT verified yet.

    with pytest.raises(AuthorizationError) as exc:
        await LoginUseCase(users=users, sessions=FakeSessionStore()).execute(
            LoginInput(phone="9876543210", password="secret123")
        )
    assert exc.value.details["code"] == "PHONE_NOT_VERIFIED"
