from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:  # Python 3.10 compatibility.
    from enum import Enum

    class StrEnum(str, Enum):
        pass
