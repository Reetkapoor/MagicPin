"""
magicpin AI Challenge — Comprehensive Test Suite
Tests endpoints, context idempotency, deterministic composer, reply engine,
case-study behaviors, taboo checks, URL checks, and canonical test pairs.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from bot import app, state, compose, sanitize_body

client = TestClient(app)
ROOT_DIR = Path(__file__).parent
DATASET_DIR = ROOT_DIR / "dataset"
EXPANDED_DIR = ROOT_DIR / "expanded"

def setup_function():
    """Reset in-memory state before each test."""
    state.reset()

def test_healthz_and_metadata():
    # Test with /v1 and without
    r1 = client.get("/v1/healthz")
    assert r1.status_code == 200
    assert r1.json()["status"] == "ok"
    assert "uptime_seconds" in r1.json()
    assert r1.json()["contexts_loaded"] == {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}

    r2 = client.get("/healthz")
    assert r2.status_code == 200

    m1 = client.get("/v1/metadata")
    assert m1.status_code == 200
    assert m1.json()["team_name"]
    assert m1.json()["version"]

    m2 = client.get("/metadata")
    assert m2.status_code == 200

def test_context_push_and_idempotency():
    # Invalid scope -> 400
    r_bad = client.post("/v1/context", json={
        "scope": "invalid",
        "context_id": "test",
        "version": 1,
        "payload": {}
    })
    assert r_bad.status_code == 400

    # Normal push v1 -> 200
    r_v1 = client.post("/v1/context", json={
        "scope": "merchant",
        "context_id": "m_test_001",
        "version": 1,
        "payload": {"name": "Test Clinic", "views": 100}
    })
    assert r_v1.status_code == 200
    assert r_v1.json()["accepted"] is True

    # Same version v1 again -> 409 stale_version
    r_v1_again = client.post("/v1/context", json={
        "scope": "merchant",
        "context_id": "m_test_001",
        "version": 1,
        "payload": {"name": "Test Clinic", "views": 100}
    })
    assert r_v1_again.status_code == 409
    assert r_v1_again.json()["accepted"] is False
    assert r_v1_again.json()["reason"] == "stale_version"

    # Higher version v2 -> 200 accepted and replaces
    r_v2 = client.post("/v1/context", json={
        "scope": "merchant",
        "context_id": "m_test_001",
        "version": 2,
        "payload": {"name": "Test Clinic", "views": 200}
    })
    assert r_v2.status_code == 200
    assert r_v2.json()["accepted"] is True
    assert state.get_context("merchant", "m_test_001")["views"] == 200

def load_seed_dataset():
    # Push categories
    for f in (DATASET_DIR / "categories").glob("*.json"):
        with open(f) as fp:
            data = json.load(fp)
            client.post("/v1/context", json={
                "scope": "category",
                "context_id": data.get("slug", f.stem),
                "version": 1,
                "payload": data
            })
    # Push merchants
    with open(DATASET_DIR / "merchants_seed.json") as fp:
        merchants = json.load(fp)["merchants"]
        for m in merchants:
            client.post("/v1/context", json={
                "scope": "merchant",
                "context_id": m["merchant_id"],
                "version": 1,
                "payload": m
            })
    # Push customers
    with open(DATASET_DIR / "customers_seed.json") as fp:
        customers = json.load(fp)["customers"]
        for c in customers:
            client.post("/v1/context", json={
                "scope": "customer",
                "context_id": c["customer_id"],
                "version": 1,
                "payload": c
            })
    # Push triggers
    with open(DATASET_DIR / "triggers_seed.json") as fp:
        triggers = json.load(fp)["triggers"]
        for t in triggers:
            client.post("/v1/context", json={
                "scope": "trigger",
                "context_id": t["id"],
                "version": 1,
                "payload": t
            })

def test_full_dataset_tick_and_suppression():
    load_seed_dataset()
    hz = client.get("/v1/healthz").json()
    assert hz["contexts_loaded"]["category"] == 5
    assert hz["contexts_loaded"]["merchant"] == 10
    assert hz["contexts_loaded"]["customer"] == 15
    assert hz["contexts_loaded"]["trigger"] == 25

    # Tick with multiple triggers across distinct merchants
    trigs = ["trg_001_research_digest_dentists", "trg_004_perf_dip_bharat", "trg_007_bridal_followup_kavya"]
    resp = client.post("/v1/tick", json={"available_triggers": trigs})
    assert resp.status_code == 200
    actions = resp.json()["actions"]
    assert len(actions) == 3

    # Ensure required fields exist in every action
    for a in actions:
        assert a["conversation_id"]
        assert a["merchant_id"]
        assert a["send_as"] in ("vera", "merchant_on_behalf")
        assert a["trigger_id"]
        assert a["template_name"]
        assert isinstance(a["template_params"], list)
        assert a["body"]
        assert a["cta"]
        assert a["suppression_key"]
        assert a["rationale"]
        # No URLs
        assert "http://" not in a["body"] and "https://" not in a["body"]

    # Calling tick again with same triggers should yield 0 actions because of suppression!
    resp2 = client.post("/v1/tick", json={"available_triggers": trigs})
    assert len(resp2.json()["actions"]) == 0

def test_ipl_saturday_contrarian_behavior():
    load_seed_dataset()
    # Trigger 10 is IPL match DC vs MI, is_weeknight = False (Saturday)
    resp = client.post("/v1/tick", json={"available_triggers": ["trg_010_ipl_match_delhi"]})
    actions = resp.json()["actions"]
    assert len(actions) == 1
    body = actions[0]["body"]
    # Must note that Saturday matches shift covers down -12%
    assert "-12%" in body
    assert "delivery" in body.lower()
    # Must NOT have taboo words
    assert "guaranteed" not in body.lower()

def test_active_planning_no_qualifying():
    load_seed_dataset()
    resp = client.post("/v1/tick", json={"available_triggers": ["trg_013_corporate_thali_planning"]})
    actions = resp.json()["actions"]
    assert len(actions) == 1
    body = actions[0]["body"]
    body_lower = body.lower()
    # Immediate action proposal
    qualifying = ["would you", "do you", "can you tell", "what if", "how about"]
    for q in qualifying:
        assert q not in body_lower
    assert "thali" in body_lower

def test_auto_reply_turn_sequence():
    # Turn 2: Warning to owner (action: send)
    r2 = client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "turn_number": 2
    })
    assert r2.status_code == 200
    assert r2.json()["action"] == "send"
    assert "auto-reply" in r2.json()["body"].lower()

    # Turn 3: Wait 86400 (action: wait)
    r3 = client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "turn_number": 3
    })
    assert r3.status_code == 200
    assert r3.json()["action"] == "wait"
    assert r3.json()["wait_seconds"] == 86400

    # Turn 4: End conversation (action: end)
    r4 = client.post("/v1/reply", json={
        "conversation_id": "conv_auto_test",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Thank you for contacting us! Our team will respond shortly.",
        "turn_number": 4
    })
    assert r4.status_code == 200
    assert r4.json()["action"] == "end"

def test_intent_transition_action_mode():
    """Matches the exact test in judge_simulator.py:740-748"""
    r = client.post("/v1/reply", json={
        "conversation_id": "conv_intent_test",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Ok lets do it. Whats next?",
        "turn_number": 2
    })
    assert r.status_code == 200
    assert r.json()["action"] == "send"
    body = r.json()["body"]
    body_lower = body.lower()
    
    qualifying = ["would you", "do you", "can you tell", "what if", "how about"]
    actioning = ["done", "sending", "draft", "here", "confirm", "proceed", "next"]
    
    assert any(w in body_lower for w in actioning), f"Expected actioning words in '{body}'"
    assert not any(w in body_lower for w in qualifying), f"Found qualifying words in '{body}'"

def test_hostile_opt_out():
    """Matches judge_simulator.py:770-780"""
    r = client.post("/v1/reply", json={
        "conversation_id": "conv_hostile_test",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Stop messaging me. This is useless spam.",
        "turn_number": 2
    })
    assert r.status_code == 200
    assert r.json()["action"] == "end"

def test_off_topic_curveball():
    r = client.post("/v1/reply", json={
        "conversation_id": "conv_curveball_test",
        "merchant_id": "m_001_drmeera_dentist_delhi",
        "from_role": "merchant",
        "message": "Btw can you also help me with my GST filing this month?",
        "turn_number": 2
    })
    assert r.status_code == 200
    assert r.json()["action"] == "send"
    assert "outside" in r.json()["body"].lower() or "consult" in r.json()["body"].lower()

def test_canonical_30_pairs():
    # Load expanded dataset if available
    test_pairs_path = EXPANDED_DIR / "test_pairs.json"
    if not test_pairs_path.exists():
        pytest.skip("expanded/test_pairs.json not found")
        
    with open(test_pairs_path) as fp:
        pairs = json.load(fp)["pairs"]
        
    # Load categories, merchants, customers, triggers from expanded
    for cat_f in (EXPANDED_DIR / "categories").glob("*.json"):
        with open(cat_f) as fp:
            d = json.load(fp)
            state.contexts[("category", d["slug"])] = {"version": 1, "payload": d}
            
    for m_f in (EXPANDED_DIR / "merchants").glob("*.json"):
        with open(m_f) as fp:
            d = json.load(fp)
            state.contexts[("merchant", d["merchant_id"])] = {"version": 1, "payload": d}
            
    for c_f in (EXPANDED_DIR / "customers").glob("*.json"):
        with open(c_f) as fp:
            d = json.load(fp)
            state.contexts[("customer", d["customer_id"])] = {"version": 1, "payload": d}
            
    for t_f in (EXPANDED_DIR / "triggers").glob("*.json"):
        with open(t_f) as fp:
            d = json.load(fp)
            state.contexts[("trigger", d["id"])] = {"version": 1, "payload": d}

    # Generate submission lines for all 30 pairs
    submission_lines = []
    for pair in pairs:
        tid = pair["trigger_id"]
        mid = pair["merchant_id"]
        cid = pair.get("customer_id")
        
        trg = state.get_context("trigger", tid)
        m = state.get_context("merchant", mid)
        c = state.get_context("customer", cid) if cid else None
        cat = state.get_context("category", m.get("category_slug"))
        
        res = compose(cat, m, trg, c)
        assert res["body"]
        assert res["cta"]
        assert res["send_as"] in ("vera", "merchant_on_behalf")
        assert res["suppression_key"]
        assert res["rationale"]
        assert "http://" not in res["body"] and "https://" not in res["body"]
        
        # Verify taboo words
        taboos = cat.get("voice", {}).get("vocab_taboo", [])
        for t in taboos:
            assert t.lower() not in res["body"].lower(), f"Taboo '{t}' found in '{res['body']}'"
            
        submission_lines.append({
            "test_id": pair["test_id"],
            "body": res["body"],
            "cta": res["cta"],
            "send_as": res["send_as"],
            "suppression_key": res["suppression_key"],
            "rationale": res["rationale"]
        })
        
    assert len(submission_lines) == 30
    
    # Write submission.jsonl as required by challenge §7.2
    submission_path = ROOT_DIR / "submission.jsonl"
    with open(submission_path, "w", encoding="utf-8") as fp:
        for item in submission_lines:
            fp.write(json.dumps(item, ensure_ascii=False) + "\n")
    assert submission_path.exists()
