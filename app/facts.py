from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Set


NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?%?)(?![A-Za-z])")


def collect_allowed_numbers(*sources: Any) -> Set[str]:
    """Collect numeric tokens from injected context only."""
    allowed: Set[str] = set()
    for source in sources:
        _collect(source, allowed)
    return allowed


def _collect(value: Any, allowed: Set[str]) -> None:
    if isinstance(value, dict):
        for v in value.values():
            _collect(v, allowed)
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            _collect(v, allowed)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        allowed.add(str(value))
        # Dataset percentages may be injected as fractions (e.g. -0.12) while
        # the outbound message renders them as -12%.
        if isinstance(value, float) and abs(value) <= 1:
            pct = value * 100
            allowed.add(f"{pct:g}%")
    elif isinstance(value, str):
        for match in NUMBER_RE.findall(value):
            allowed.add(match)


def numeric_tokens(text: str) -> Set[str]:
    return set(NUMBER_RE.findall(text))


def grounded_numeric_tokens(text: str, allowed_numbers: Iterable[str]) -> bool:
    allowed = set(allowed_numbers)
    return numeric_tokens(text).issubset(allowed)


def merchant_facts(merchant: Dict[str, Any]) -> Dict[str, Any]:
    """Return only injected merchant facts used for grounded composition."""
    return {
        "merchant_name": merchant.get("identity", {}).get("name"),
        "locality": merchant.get("identity", {}).get("locality"),
        "city": merchant.get("identity", {}).get("city"),
        "performance": merchant.get("performance", {}),
        "subscription": merchant.get("subscription", {}),
        "customer_aggregate": merchant.get("customer_aggregate", {}),
        "offers": merchant.get("offers", []),
    }
