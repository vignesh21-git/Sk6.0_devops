from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.repositories import UserRepository
from app.application.interfaces.services import OtpStore, SessionStore
from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.domain.entities.user import User
from app.infrastructure.cache.otp_store import RedisOtpStore
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.cache.session_store import RedisSessionStore
from app.infrastructure.db.repositories.user import SqlAlchemyUserRepository
from app.infrastructure.db.session import SessionFactory
from app.infrastructure.external.otp_gateway import (
    OtpGateway,
    make_otp_gateway,
)


# ─── DB session ────────────────────────────────────────────
async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ─── Repositories & stores ────────────────────────────────
def get_user_repository(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_session_store() -> SessionStore:
    return RedisSessionStore(get_redis())


def get_otp_store() -> OtpStore:
    return RedisOtpStore(get_redis())


def get_otp_gateway() -> OtpGateway:
    return make_otp_gateway()


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
SessionStoreDep = Annotated[SessionStore, Depends(get_session_store)]
OtpStoreDep = Annotated[OtpStore, Depends(get_otp_store)]
OtpGatewayDep = Annotated[OtpGateway, Depends(get_otp_gateway)]


# ─── Auth ─────────────────────────────────────────────────
def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError(
            "Missing or invalid Authorization header",
            details={"code": "MISSING_BEARER_TOKEN"},
        )
    return authorization.split(" ", 1)[1].strip()


async def get_current_session(
    authorization: Annotated[str | None, Header()] = None,
    sessions: SessionStoreDep = ...,
) -> tuple[dict, str]:
    """Returns (decoded_jwt_payload, jti)."""
    token = _extract_bearer_token(authorization)
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(
            "Token expired", details={"code": "TOKEN_EXPIRED"}
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(
            "Invalid token", details={"code": "TOKEN_INVALID"}
        ) from exc

    jti = payload.get("jti")
    if not jti:
        raise AuthenticationError(
            "Token missing jti", details={"code": "TOKEN_INVALID"}
        )

    record = await sessions.get(jti)
    if record is None:
        raise AuthenticationError(
            "Session revoked or expired",
            details={"code": "SESSION_REVOKED"},
        )

    return payload, jti


CurrentSession = Annotated[tuple[dict, str], Depends(get_current_session)]


async def get_current_user(
    current: CurrentSession,
    users: UserRepoDep,
) -> User:
    payload, _jti = current
    user = await users.get_by_id(uuid.UUID(payload["sub"]))
    if user is None:
        raise AuthenticationError(
            "User no longer exists",
            details={"code": "USER_NOT_FOUND"},
        )
    if user.is_blocked:
        raise AuthenticationError(
            "Account blocked", details={"code": "USER_BLOCKED"}
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
