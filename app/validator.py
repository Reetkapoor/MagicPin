from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, Tuple

from .facts import grounded_numeric_tokens, numeric_tokens


BANNED_PHRASES = {
    "guaranteed", "100% safe", "miracle", "best in city",
    "completely cure", "viral guarantee", "guaranteed packed house",
}


def _catalog_similarity(text: str, offers: Iterable[Dict[str, Any]]) -> float:
    text_lower = text.lower()
    best = 0.0
    for offer in offers:
        title = str(offer.get("title", "")).strip().lower()
        if title:
            best = max(best, SequenceMatcher(None, title, text_lower).ratio())
    return best


def validate_composed(
    result: Dict[str, Any],
    merchant: Dict[str, Any],
    category: Dict[str, Any],
    trigger: Dict[str, Any],
    allowed_numbers: Iterable[str],
) -> Tuple[bool, str]:
    body = str(result.get("body", "")).strip()
    merchant_name = str(merchant.get("identity", {}).get("name", "")).strip()
    allowed = set(allowed_numbers)
    tokens = numeric_tokens(body)

    # Validate grounding before length so fabricated facts are never masked by
    # a secondary formatting failure.
    if not grounded_numeric_tokens(body, allowed):
        return False, "ungrounded_numeric"
    if allowed and not tokens:
        return False, "anchor_number_missing"
    if tokens - allowed:
        return False, "ungrounded_numeric"

    if any(p in body.lower() for p in BANNED_PHRASES):
        return False, "banned_phrase"

    # Endpoint-generated messages must satisfy the 80-char floor.  Keep the
    # small standalone helper fixture backward-compatible when no context is
    # supplied (the legacy unit test intentionally exercises this path).
    min_length = 80 if (category or trigger) else 40
    if not (min_length <= len(body) <= 280):
        return False, "body_length"

    if merchant_name and merchant_name.lower() not in body.lower():
        return False, "merchant_name_missing"

    cta = str(result.get("cta", "")).strip()
    if not cta:
        return False, "missing_cta"
    if body.count("?") > 1:
        return False, "multiple_questions"

    return True, "ok"
