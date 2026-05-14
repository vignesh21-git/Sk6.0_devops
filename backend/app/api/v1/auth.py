from __future__ import annotations

from fastapi import APIRouter, status

from app.api.v1.deps import (
    CurrentSession,
    OtpGatewayDep,
    OtpStoreDep,
    SessionStoreDep,
    UserRepoDep,
)
from app.application.use_cases.auth.login import LoginInput, LoginUseCase
from app.application.use_cases.auth.logout import LogoutInput, LogoutUseCase
from app.application.use_cases.auth.register import (
    RegisterUserInput,
    RegisterUserUseCase,
)
from app.application.use_cases.auth.request_otp import (
    RequestOtpInput,
    RequestOtpUseCase,
)
from app.application.use_cases.auth.verify_otp import (
    VerifyOtpInput,
    VerifyOtpUseCase,
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RegisterRequest,
    RegisterResponse,
    RequestOtpRequest,
    RequestOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    users: UserRepoDep,
    otp_store: OtpStoreDep,
    otp_gateway: OtpGatewayDep,
) -> RegisterResponse:
    out = await RegisterUserUseCase(
        users=users, otp_store=otp_store, otp_gateway=otp_gateway
    ).execute(
        RegisterUserInput(
            phone=body.phone, password=body.password, full_name=body.full_name
        )
    )
    return RegisterResponse(
        user_id=out.user_id,
        phone=out.phone,
        status=out.status,
        phone_verified=out.phone_verified,
    )


@router.post("/request-otp", response_model=RequestOtpResponse)
async def request_otp(
    body: RequestOtpRequest,
    users: UserRepoDep,
    otp_store: OtpStoreDep,
    otp_gateway: OtpGatewayDep,
) -> RequestOtpResponse:
    out = await RequestOtpUseCase(
        users=users, otp_store=otp_store, otp_gateway=otp_gateway
    ).execute(RequestOtpInput(phone=body.phone))
    return RequestOtpResponse(
        phone=out.phone, expires_in_seconds=out.expires_in_seconds
    )


@router.post("/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(
    body: VerifyOtpRequest,
    users: UserRepoDep,
    otp_store: OtpStoreDep,
) -> VerifyOtpResponse:
    out = await VerifyOtpUseCase(users=users, otp_store=otp_store).execute(
        VerifyOtpInput(phone=body.phone, otp=body.otp)
    )
    return VerifyOtpResponse(
        phone=out.phone,
        phone_verified=out.phone_verified,
        status=out.status,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    users: UserRepoDep,
    sessions: SessionStoreDep,
) -> LoginResponse:
    out = await LoginUseCase(users=users, sessions=sessions).execute(
        LoginInput(phone=body.phone, password=body.password)
    )
    return LoginResponse(
        access_token=out.access_token,
        token_type=out.token_type,
        expires_in=out.expires_in,
        user_id=out.user_id,
        role=out.role,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current: CurrentSession,
    sessions: SessionStoreDep,
) -> LogoutResponse:
    _payload, jti = current
    await LogoutUseCase(sessions=sessions).execute(LogoutInput(jti=jti))
    return LogoutResponse()
