from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def suppression_key(trigger: Dict[str, Any], now: str) -> str:
    """Deterministic weekly suppression key derived from trigger identity and request time."""
    dt = datetime.fromisoformat(now.replace("Z", "+00:00"))
    iso = dt.isocalendar()
    trigger_type = trigger.get("kind", "unknown")
    category = trigger.get("category_slug") or trigger.get("category") or "unknown"
    merchant_id = trigger.get("merchant_id", "unknown")
    return f"{trigger_type}:{category}:{merchant_id}:{iso.year}-W{iso.week:02d}"


def is_suppressed(store: Any, key: str) -> bool:
    return key in store.suppressions
