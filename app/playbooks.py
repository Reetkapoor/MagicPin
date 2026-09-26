from __future__ import annotations

from typing import Any, Dict


PLAYBOOKS: Dict[str, Dict[str, Any]] = {
    "research_digest": {
        "goal": "surface one relevant injected research item",
        "cta": "open_ended",
    },
    "compliance": {
        "goal": "surface a compliance deadline or change from context",
        "cta": "binary_yes_no",
    },
    "performance_dip": {
        "goal": "address an injected performance decline with one concrete action",
        "cta": "binary_yes_no",
    },
    "seasonal_event": {
        "goal": "connect an injected seasonal event to a merchant action",
        "cta": "binary_yes_no",
    },
    "peer_gap": {
        "goal": "use only injected peer comparison facts",
        "cta": "binary_yes_no",
    },
    "customer_lapse": {
        "goal": "reactivate a customer using only injected lapse facts",
        "cta": "binary_yes_no",
    },
    "performance_spike": {
        "goal": "reinforce an injected performance improvement",
        "cta": "binary_yes_no",
    },
}


def get_playbook(kind: str) -> Dict[str, Any]:
    return PLAYBOOKS.get(kind, {
        "goal": "advance the merchant conversation with one concrete next step",
        "cta": "binary_yes_no",
    })
