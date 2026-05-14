import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    *, user_id: str, role: str, jti: str | None = None
) -> tuple[str, str, datetime]:
    """Issue a signed JWT.

    Returns (token, jti, expires_at). The caller is responsible for storing
    the jti in Redis so the session can be revoked before token expiry.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=settings.jwt_expire_hours)
    jti = jti or str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "role": role,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, exp


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
