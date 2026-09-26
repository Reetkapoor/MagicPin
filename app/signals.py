from __future__ import annotations

from typing import Any, Dict, Iterable, List


SIGNAL_WEIGHTS = {
    "compliance": 1.10,
    "performance_dip": 1.00,
    "seasonal_event": 0.95,
    "peer_gap": 0.90,
    "customer_lapse": 0.85,
    "performance_spike": 0.80,
    "research_digest": 0.60,
}


def score_trigger(trigger: Dict[str, Any]) -> float:
    kind = str(trigger.get("kind", ""))
    base = SIGNAL_WEIGHTS.get(kind, 0.50)
    urgency = float(trigger.get("urgency", 1) or 1)
    novelty = float(trigger.get("novelty", 1) or 1)
    category_fit = float(trigger.get("category_fit", 1) or 1)
    return base * urgency * novelty * category_fit


def rank_triggers(triggers: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        triggers,
        key=lambda t: (
            score_trigger(t),
            str(t.get("trigger_id") or t.get("id") or ""),
        ),
        reverse=True,
    )


def select_triggers(triggers: Iterable[Dict[str, Any]], max_actions: int = 20) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    seen_merchants = set()
    for trigger in rank_triggers(triggers):
        merchant_id = trigger.get("merchant_id")
        if not merchant_id or merchant_id in seen_merchants:
            continue
        selected.append(trigger)
        seen_merchants.add(merchant_id)
        if len(selected) >= max_actions:
            break
    return selected
