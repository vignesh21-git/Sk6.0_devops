from __future__ import annotations

from redis.asyncio import Redis

from app.application.interfaces.services import OtpRecord, OtpStore


def _otp_key(phone: str) -> str:
    return f"otp:{phone}"


def _attempts_key(phone: str) -> str:
    return f"otp_attempts:{phone}"


class RedisOtpStore(OtpStore):
    def __init__(self, redis: Redis) -> None:
        self._r = redis

    async def put(
        self, *, phone: str, code: str, ttl_seconds: int
    ) -> None:
        async with self._r.pipeline() as pipe:
            pipe.set(_otp_key(phone), code, ex=ttl_seconds)
            pipe.set(_attempts_key(phone), 0, ex=ttl_seconds)
            await pipe.execute()

    async def get(self, phone: str) -> OtpRecord | None:
        code = await self._r.get(_otp_key(phone))
        if code is None:
            return None
        attempts_raw = await self._r.get(_attempts_key(phone))
        attempts = int(attempts_raw) if attempts_raw is not None else 0
        return OtpRecord(code=code, attempts=attempts)

    async def increment_attempts(self, phone: str) -> int:
        return await self._r.incr(_attempts_key(phone))

    async def delete(self, phone: str) -> None:
        await self._r.delete(_otp_key(phone), _attempts_key(phone))
