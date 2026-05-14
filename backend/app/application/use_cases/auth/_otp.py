import secrets

from app.core.config import get_settings


def generate_otp() -> str:
    """Numeric OTP of `settings.otp_length` digits, zero-padded."""
    length = get_settings().otp_length
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"
