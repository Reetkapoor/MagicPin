from app.signals import score_trigger, select_triggers
from app.suppression import suppression_key


def test_signal_weights_and_one_per_merchant():
    compliance = {"kind": "compliance", "merchant_id": "m1", "urgency": 1}
    research = {"kind": "research_digest", "merchant_id": "m2", "urgency": 1}
    assert score_trigger(compliance) > score_trigger(research)
    selected = select_triggers([research, compliance, {"kind": "performance_dip", "merchant_id": "m1", "urgency": 1}])
    assert [x["merchant_id"] for x in selected].count("m1") == 1


def test_weekly_suppression_is_request_time_deterministic():
    trigger = {"kind": "performance_dip", "category_slug": "restaurants", "merchant_id": "m1"}
    assert suppression_key(trigger, "2026-09-26T10:00:00Z") == "performance_dip:restaurants:m1:2026-W39"
