from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    phone: str
    full_name: str | None
    status: str
    role: str
    phone_verified: bool
    last_login_at: datetime | None
    created_at: datetime
