from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.exceptions import InvariantViolation

# Indian mobile: 10 digits, must start with 6/7/8/9.
_PHONE_RE = re.compile(r"^[6-9]\d{9}$")


@dataclass(frozen=True, slots=True)
class Phone:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().replace(" ", "").replace("-", "")
        if normalized.startswith("+91"):
            normalized = normalized[3:]
        elif normalized.startswith("91") and len(normalized) == 12:
            normalized = normalized[2:]
        elif normalized.startswith("0") and len(normalized) == 11:
            normalized = normalized[1:]

        if not _PHONE_RE.match(normalized):
            raise InvariantViolation(
                "Invalid Indian mobile number",
                details={"input": self.value},
            )
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
