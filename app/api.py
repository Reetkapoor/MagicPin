from __future__ import annotations

import json
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .composer import compose, get_category_for_merchant, handle_reply
from .schemas import (
    ContextAcceptedResponse, ContextRequest, MetadataResponse, TickRequest,
    ReplyRequest, ReplyResponse, TickAction, TickResponse, HealthResponse,
)
from .store import state
from .config import MAX_CONTEXT_BYTES, MAX_TICK_ACTIONS
from .facts import collect_allowed_numbers
from .signals import select_triggers
from .suppression import suppression_key
from .validator import validate_composed

app = FastAPI(title="Vera Merchant AI Assistant", version="1.0.0")
START_TIME = time.time()


@app.get("/healthz", response_model=HealthResponse)
@app.get("/v1/healthz", response_model=HealthResponse)
async def healthz():
    return {"status": "ok", "uptime_seconds": int(time.time() - START_TIME), "contexts_loaded": state.get_counts()}


@app.get("/metadata", response_model=MetadataResponse)
@app.get("/v1/metadata", response_model=MetadataResponse)
async def metadata():
    return {
        "team_name": "Team VERA Deterministic",
        "team_members": ["Participant"],
        "model": "deterministic-expert-system",
        "approach": "deterministic dispatch-by-kind with strict context grounding and suppression management",
        "contact_email": "participant@magicpin.example.com",
        "version": "1.0.0",
        "submitted_at": "2026-04-26T08:00:00Z",
    }


@app.post("/context")
@app.post("/v1/context")
async def push_context(body: ContextRequest):
    if body.scope not in ("category", "merchant", "customer", "trigger"):
        return JSONResponse(status_code=400, content={
            "accepted": False, "reason": "invalid_scope",
            "details": f"Unknown scope: {body.scope}",
        })
    payload_bytes = len(json.dumps(body.payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    if payload_bytes > MAX_CONTEXT_BYTES:
        return JSONResponse(status_code=400, content={"accepted": False, "reason": "payload_too_large"})
    if not state.put_context(body.scope, body.context_id, body.version, body.payload):
        return JSONResponse(status_code=409, content={
            "accepted": False, "reason": "stale_version",
            "current_version": state.get_version(body.scope, body.context_id),
        })
    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": body.delivered_at or "1970-01-01T00:00:00+00:00",
    }


@app.post("/tick", response_model=TickResponse)
@app.post("/v1/tick", response_model=TickResponse)
async def tick(body: TickRequest):
    candidates = []
    for trg_id in body.available_triggers:
        trg = state.get_context("trigger", trg_id)
        if not trg:
            continue
        item = dict(trg)
        item["_trigger_id"] = trg_id
        candidates.append(item)

    actions = []
    merchants_messaged_this_tick = set()
    for trg in select_triggers(candidates, max_actions=MAX_TICK_ACTIONS):
        trg_id = trg.get("_trigger_id") or trg.get("trigger_id") or trg.get("id")
        m_id = trg.get("merchant_id")
        if not m_id or m_id in merchants_messaged_this_tick or m_id in state.opted_out_merchants:
            continue

        merchant = state.get_context("merchant", m_id)
        if not merchant:
            continue
        category = get_category_for_merchant(merchant)
        customer = state.get_context("customer", trg.get("customer_id")) if trg.get("customer_id") else None

        key = suppression_key(trg, body.now) if body.now else trg.get("suppression_key", "")
        if key and key in state.suppressions:
            continue

        trigger_for_compose = dict(trg)
        if key:
            trigger_for_compose["suppression_key"] = key

        composed = compose(category, merchant, trigger_for_compose, customer)
        allowed_numbers = collect_allowed_numbers(category, merchant, trigger_for_compose, customer)
        valid, _reason = validate_composed(
            composed, merchant, category, trigger_for_compose, allowed_numbers
        )

        # One deterministic fallback attempt after validation failure.
        if not valid:
            merchant_name = merchant.get("identity", {}).get("name", "your business")
            locality = merchant.get("identity", {}).get("locality") or merchant.get("identity", {}).get("city") or ""
            body_text = (
                f"{merchant_name}, Vera has a relevant update for your business"
                + (f" in {locality}." if locality else ".")
                + " I can prepare the next step using the information already provided. "
                "Would you like me to proceed?"
            )
            composed = {
                **composed,
                "body": body_text,
                "cta": "binary_yes_no",
                "rationale": "Deterministic grounded fallback after outbound validation.",
                "template_name": "vera_grounded_fallback_v1",
                "template_params": [merchant_name],
            }

        conv_id = f"conv_{m_id}_{trg_id}"
        actions.append({
            "conversation_id": conv_id,
            "merchant_id": m_id,
            "customer_id": trg.get("customer_id"),
            "send_as": composed["send_as"],
            "trigger_id": trg_id,
            "template_name": composed["template_name"],
            "template_params": composed["template_params"],
            "body": composed["body"],
            "cta": composed["cta"],
            "suppression_key": key or composed["suppression_key"],
            "rationale": composed["rationale"],
        })
        merchants_messaged_this_tick.add(m_id)
        if key:
            state.suppressions.add(key)
        state.merchant_active_conv[m_id] = conv_id
        state.conversations.setdefault(conv_id, []).append({
            "from": "vera",
            "body": composed["body"],
            "ts": body.now or "1970-01-01T00:00:00+00:00",
        })

    return {"actions": actions}


@app.post("/reply", response_model=ReplyResponse)
@app.post("/v1/reply", response_model=ReplyResponse)
async def reply(body: ReplyRequest):
    conv_history = state.conversations.setdefault(body.conversation_id, [])
    event_ts = body.received_at or "1970-01-01T00:00:00+00:00"
    conv_history.append({
        "from": body.from_role, "msg": body.message,
        "ts": event_ts, "turn": body.turn_number,
    })
    merchant = state.get_context("merchant", body.merchant_id) if body.merchant_id else None
    result = handle_reply(body.conversation_id, body.message, body.turn_number, merchant)
    if result.get("action") == "send":
        conv_history.append({"from": "vera", "body": result.get("body", ""), "ts": event_ts})
    return result


@app.post("/teardown")
@app.post("/v1/teardown")
async def teardown():
    state.reset()
    return {"status": "ok", "message": "State wiped cleanly"}
