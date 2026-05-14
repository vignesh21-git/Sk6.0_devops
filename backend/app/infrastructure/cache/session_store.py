from __future__ import annotations

import json
import uuid
from datetime import datetime

from redis.asyncio import Redis

from app.application.interfaces.services import SessionRecord, SessionStore


def _session_key(jti: str) -> str:
    return f"session:{jti}"


def _user_sessions_set(user_id: uuid.UUID) -> str:
    return f"user_sessions:{user_id}"


class RedisSessionStore(SessionStore):
    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def put(
        self, *, jti: str, record: SessionRecord, ttl_seconds: int
    ) -> None:
        payload = json.dumps(
            {
                "user_id": str(record.user_id),
                "role": record.role,
                "issued_at": record.issued_at.isoformat(),
            }
        )
        async with self._r.pipeline() as pipe:
            pipe.set(_session_key(jti), payload, ex=ttl_seconds)
            pipe.sadd(_user_sessions_set(record.user_id), jti)
            pipe.expire(
                _user_sessions_set(record.user_id), ttl_seconds
            )
            await pipe.execute()

    async def get(self, jti: str) -> SessionRecord | None:
        raw = await self._r.get(_session_key(jti))
        if raw is None:
            return None
        data = json.loads(raw)
        return SessionRecord(
            user_id=uuid.UUID(data["user_id"]),
            role=data["role"],
            issued_at=datetime.fromisoformat(data["issued_at"]),
        )

    async def revoke(self, jti: str) -> None:
        record = await self.get(jti)
        async with self._r.pipeline() as pipe:
            pipe.delete(_session_key(jti))
            if record is not None:
                pipe.srem(_user_sessions_set(record.user_id), jti)
            await pipe.execute()

    async def revoke_user_sessions(self, user_id: uuid.UUID) -> int:
        set_key = _user_sessions_set(user_id)
        jtis = await self._r.smembers(set_key)
        if not jtis:
            return 0
        keys = [_session_key(j) for j in jtis] + [set_key]
        await self._r.delete(*keys)
        return len(jtis)
