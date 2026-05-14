from __future__ import annotations

from dataclasses import dataclass

from app.application.interfaces.services import SessionStore


@dataclass(slots=True)
class LogoutInput:
    jti: str


class LogoutUseCase:
    def __init__(self, *, sessions: SessionStore) -> None:
        self._sessions = sessions

    async def execute(self, data: LogoutInput) -> None:
        await self._sessions.revoke(data.jti)
