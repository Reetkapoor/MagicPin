#!/usr/bin/env python3
"""Phase 5 offline scorecard: compare the preserved baseline bot with app/."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASELINE_COMMIT = "ec9c2d114991d3862120a739e28af0bffd98d153"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_dataset():
    categories = {}
    for p in (ROOT / "dataset" / "categories").glob("*.json"):
        data = load_json(p)
        categories[data.get("slug", p.stem)] = data
    merchants = {x["merchant_id"]: x for x in load_json(ROOT / "dataset" / "merchants_seed.json")["merchants"]}
    customers = {x["customer_id"]: x for x in load_json(ROOT / "dataset" / "customers_seed.json")["customers"]}
    triggers = {x["id"]: x for x in load_json(ROOT / "dataset" / "triggers_seed.json")["triggers"]}
    return categories, merchants, customers, triggers


def load_baseline():
    source = subprocess.check_output(
        ["git", "show", f"{BASELINE_COMMIT}:bot.py"], cwd=ROOT, text=True
    )
    with tempfile.NamedTemporaryFile("w", suffix="_baseline_bot.py", delete=False, encoding="utf-8") as f:
        f.write(source)
        path = f.name
    spec = spec_from_file_location("baseline_bot", path)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def seed_client(client, categories, merchants, customers, triggers):
    for cid, category in categories.items():
        client.post("/v1/context", json={
            "scope": "category", "context_id": cid, "version": 1, "payload": category,
            "delivered_at": "2026-09-26T12:00:00Z",
        })
    for mid, merchant in merchants.items():
        client.post("/v1/context", json={
            "scope": "merchant", "context_id": mid, "version": 1, "payload": merchant,
            "delivered_at": "2026-09-26T12:00:00Z",
        })
    for cid, customer in customers.items():
        client.post("/v1/context", json={
            "scope": "customer", "context_id": cid, "version": 1, "payload": customer,
            "delivered_at": "2026-09-26T12:00:00Z",
        })
    for tid, trigger in triggers.items():
        client.post("/v1/context", json={
            "scope": "trigger", "context_id": tid, "version": 1, "payload": trigger,
            "delivered_at": "2026-09-26T12:00:00Z",
        })


def collect_actions(client, trigger_ids):
    r = client.post("/v1/tick", json={
        "now": "2026-09-26T12:00:00Z", "available_triggers": trigger_ids
    })
    if r.status_code != 200:
        return [], {"http_status": r.status_code}
    return r.json().get("actions", []), {}


def action_quality(action, merchant):
    body = action.get("body", "")
    name = merchant.get("identity", {}).get("name", "")
    return {
        "length_ok": 80 <= len(body) <= 280,
        "merchant_name_present": bool(name) and name.lower() in body.lower(),
        "cta_present": bool(action.get("cta")),
        "schema_keys_present": all(k in action for k in (
            "conversation_id", "merchant_id", "customer_id", "send_as",
            "trigger_id", "template_name", "template_params", "body",
            "cta", "suppression_key", "rationale",
        )),
    }


def main():
    categories, merchants, customers, triggers = load_dataset()
    trigger_ids = list(triggers)

    # New implementation.
    from fastapi.testclient import TestClient
    from app.api import app as new_app

    with TestClient(new_app) as new_client:
        seed_client(new_client, categories, merchants, customers, triggers)
        new_actions, new_error = collect_actions(new_client, trigger_ids)

    # Baseline implementation at the original one-commit state.
    baseline = load_baseline()
    with TestClient(baseline.app) as old_client:
        for cid, category in categories.items():
            old_client.post("/v1/context", json={"scope": "category", "context_id": cid, "version": 1, "payload": category})
        for mid, merchant in merchants.items():
            old_client.post("/v1/context", json={"scope": "merchant", "context_id": mid, "version": 1, "payload": merchant})
        for cid, customer in customers.items():
            old_client.post("/v1/context", json={"scope": "customer", "context_id": cid, "version": 1, "payload": customer})
        for tid, trigger in triggers.items():
            old_client.post("/v1/context", json={"scope": "trigger", "context_id": tid, "version": 1, "payload": trigger})
        old_actions, old_error = collect_actions(old_client, trigger_ids)

    def summarize(actions):
        qualities = []
        for action in actions:
            merchant = merchants.get(action.get("merchant_id"), {})
            qualities.append(action_quality(action, merchant))
        return {
            "actions": len(actions),
            "unique_merchants": len({a.get("merchant_id") for a in actions}),
            "schema_complete": sum(q["schema_keys_present"] for q in qualities),
            "length_ok": sum(q["length_ok"] for q in qualities),
            "merchant_name_present": sum(q["merchant_name_present"] for q in qualities),
            "cta_present": sum(q["cta_present"] for q in qualities),
        }

    result = {
        "baseline_commit": BASELINE_COMMIT,
        "dataset": {"categories": len(categories), "merchants": len(merchants),
                    "customers": len(customers), "triggers": len(triggers)},
        "baseline": {"error": old_error, **summarize(old_actions)},
        "migrated": {"error": new_error, **summarize(new_actions)},
        "determinism": None,
    }

    with TestClient(new_app) as client:
        seed_client(client, categories, merchants, triggers)
        a1, _ = collect_actions(client, trigger_ids)
    with TestClient(new_app) as client:
        seed_client(client, categories, merchants, triggers)
        a2, _ = collect_actions(client, trigger_ids)
    result["determinism"] = a1 == a2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
