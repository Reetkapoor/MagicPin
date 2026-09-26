from app.validator import validate_composed


def test_validator_rejects_ungrounded_numbers():
    merchant = {"identity": {"name": "Test Cafe"}}
    result = {
        "body": "Test Cafe has 999 new views this week. Want me to proceed?",
        "cta": "binary_yes_no",
    }
    ok, reason = validate_composed(result, merchant, {}, {}, {"42"})
    assert not ok
    assert reason == "ungrounded_numeric"


def test_validator_accepts_grounded_message():
    merchant = {"identity": {"name": "Test Cafe"}}
    result = {
        "body": "Test Cafe has 42 new views this week. Want me to proceed?",
        "cta": "binary_yes_no",
    }
    ok, reason = validate_composed(result, merchant, {}, {}, {"42"})
    assert ok
