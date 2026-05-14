from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.deps import CurrentUser
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut(
        id=str(user.id),
        phone=user.phone.value,
        full_name=user.full_name,
        status=user.status.value,
        role=user.role.value,
        phone_verified=user.phone_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )
