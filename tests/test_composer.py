from app.composer import compose


def test_ipl_composition_preserves_baseline_branch():
    category = {"slug": "restaurants", "voice": {"vocab_taboo": []}}
    merchant = {
        "merchant_id": "m1",
        "category_slug": "restaurants",
        "identity": {"name": "Test Cafe", "owner_first_name": "Reet", "locality": "Noida", "city": "Noida"},
        "offers": [{"title": "BOGO pizza", "status": "active"}],
        "performance": {},
        "subscription": {},
        "customer_aggregate": {},
    }
    trigger = {
        "kind": "ipl_match_today",
        "scope": "merchant",
        "payload": {"match": "DC vs MI", "venue": "Arun Jaitley Stadium", "is_weeknight": False},
        "suppression_key": "test",
    }
    result = compose(category, merchant, trigger)
    assert "-12%" in result["body"]
    assert "delivery" in result["body"].lower()
