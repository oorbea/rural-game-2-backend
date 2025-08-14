from datetime import date, datetime
import json
from typing import Any

def normalize_value(v: Any) -> str | int | float:
    """Normalize Python values to Redis-compatible types."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float, str)):
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    try:
        from enum import Enum
        if isinstance(v, Enum):
            return str(v.value)
    except Exception:
        pass
    return json.dumps(v, separators=(",", ":"))