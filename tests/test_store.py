from app.store import StateStore


def test_store_versioning_snapshot_and_indexes():
    store = StateStore()
    assert store.put_context("merchant", "m1", 1, {"name": "A"})
    assert not store.put_context("merchant", "m1", 1, {"name": "B"})
    assert store.put_context("merchant", "m1", 2, {"name": "B"})
    snap = store.get_context_snapshot("merchant", "m1")
    assert snap["name"] == "B"
    assert store.get_scope_ids("merchant") == ("m1",)
    assert store.get_counts()["merchant"] == 1
    try:
        snap["name"] = "C"
        assert False, "snapshot must be immutable"
    except TypeError:
        pass
