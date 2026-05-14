from abc import ABC, abstractmethod

import structlog

log = structlog.get_logger(__name__)


class OtpGateway(ABC):
    @abstractmethod
    async def send_otp(self, *, phone: str, otp: str) -> None: ...


class DevStubOtpGateway(OtpGateway):
    """Logs OTP to stdout. NEVER use in production."""

    async def send_otp(self, *, phone: str, otp: str) -> None:
        log.info("otp_dispatched", phone=phone, otp=otp, gateway="dev-stub")


def make_otp_gateway() -> OtpGateway:
    # Real zplusone adapter swaps in here behind the same interface.
    return DevStubOtpGateway()
