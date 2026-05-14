from __future__ import annotations

import uuid

from app.application.interfaces.services import (
    OtpRecord,
    OtpStore,
    SessionRecord,
    SessionStore,
)


class FakeOtpStore(OtpStore):
    def __init__(self) -> None:
        self.codes: dict[str, str] = {}
        self.attempts: dict[str, int] = {}

    async def put(
        self, *, phone: str, code: str, ttl_seconds: int
    ) -> None:
        self.codes[phone] = code
        self.attempts[phone] = 0

    async def get(self, phone: str) -> OtpRecord | None:
        if phone not in self.codes:
            return None
        return OtpRecord(code=self.codes[phone], attempts=self.attempts[phone])

    async def increment_attempts(self, phone: str) -> int:
        self.attempts[phone] = self.attempts.get(phone, 0) + 1
        return self.attempts[phone]

    async def delete(self, phone: str) -> None:
        self.codes.pop(phone, None)
        self.attempts.pop(phone, None)


class FakeSessionStore(SessionStore):
    def __init__(self) -> None:
        self.sessions: dict[str, SessionRecord] = {}

    async def put(
        self, *, jti: str, record: SessionRecord, ttl_seconds: int
    ) -> None:
        self.sessions[jti] = record

    async def get(self, jti: str) -> SessionRecord | None:
        return self.sessions.get(jti)

    async def revoke(self, jti: str) -> None:
        self.sessions.pop(jti, None)

    async def revoke_user_sessions(self, user_id: uuid.UUID) -> int:
        to_remove = [
            j for j, r in self.sessions.items() if r.user_id == user_id
        ]
        for j in to_remove:
            del self.sessions[j]
        return len(to_remove)
