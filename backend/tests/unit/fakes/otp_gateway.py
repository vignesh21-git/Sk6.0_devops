from __future__ import annotations

from app.infrastructure.external.otp_gateway import OtpGateway


class FakeOtpGateway(OtpGateway):
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_otp(self, *, phone: str, otp: str) -> None:
        self.sent.append((phone, otp))
