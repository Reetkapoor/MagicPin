from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager

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

START_TIME = time.monotonic()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    state.reset()
    yield


app = FastAPI(title="Vera Merchant AI Assistant", version="1.0.0", lifespan=lifespan)


@app.get("/healthz", response_model=HealthResponse)
@app.get("/v1/healthz", response_model=HealthResponse)
@app.get("/")\nasync def demo_ui():\n    from fastapi.responses import FileResponse\n    return FileResponse("static/index.html")\n\n\nasync def healthz():
    return {"status": "ok", "uptime_seconds": int(time.monotonic() - START_TIME), "contexts_loaded": state.get_counts()}


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


async def _process_trigger(trg, now: str, deadline: float):
    if time.monotonic() >= deadline:
        return None

    trg_id = trg.get("_trigger_id") or trg.get("trigger_id") or trg.get("id")
    m_id = trg.get("merchant_id")
    if not m_id or m_id in state.opted_out_merchants:
        return None

    merchant = state.get_context("merchant", m_id)
    if not merchant:
        return None
    category = get_category_for_merchant(merchant)
    customer = state.get_context("customer", trg.get("customer_id")) if trg.get("customer_id") else None
    key = suppression_key(trg, now) if now else trg.get("suppression_key", "")
    if key and not state.reserve_suppression(key):
        return None

    try:
        trigger_for_compose = dict(trg)
        if key:
            trigger_for_compose["suppression_key"] = key

        composed = compose(category, merchant, trigger_for_compose, customer)
        allowed_numbers = collect_allowed_numbers(category, merchant, trigger_for_compose, customer)
        valid, _reason = validate_composed(
            composed, merchant, category, trigger_for_compose, allowed_numbers
        )

        if not valid:
            merchant_name = merchant.get("identity", {}).get("name", "your business")
            locality = merchant.get("identity", {}).get("locality") or merchant.get("identity", {}).get("city") or ""
            anchor = sorted(allowed_numbers)[0] if allowed_numbers else None
            body_text = (
                f"{merchant_name}, Vera has a relevant update for your business"
                + (f" in {locality}." if locality else ".")
                + (f" The injected context includes {anchor} as a relevant reference." if anchor else "")
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
        state.merchant_active_conv[m_id] = conv_id
        state.conversations.setdefault(conv_id, []).append({
            "from": "vera", "body": composed["body"], "ts": now
        })
        return {
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
        }
    except Exception:
        # Fail-safe: never let one malformed trigger make /tick return 500.
        if key:
            state.release_suppression(key)
        return None


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

    selected = select_triggers(candidates, max_actions=MAX_TICK_ACTIONS)
    deadline = time.monotonic() + 14.0
    sem = asyncio.Semaphore(8)

    async def bounded(trg):
        async with sem:
            return await _process_trigger(trg, body.now or "1970-01-01T00:00:00+00:00", deadline)

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(bounded(trg) for trg in selected), return_exceptions=True),
            timeout=14.5,
        )
    except asyncio.TimeoutError:
        results = []

    actions = [r for r in results if isinstance(r, dict)]
    actions.sort(key=lambda a: a["trigger_id"])
    return {"actions": actions}


@app.post("/reply", response_model=ReplyResponse)
@app.post("/v1/reply", response_model=ReplyResponse)
async def reply(body: ReplyRequest):
    try:
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
    except Exception:
        return {"action": "wait", "wait_seconds": 30, "rationale": "Temporary processing failure; no outbound message sent."}


@app.post("/teardown")
@app.post("/v1/teardown")
async def teardown():
    state.reset()
    return {"status": "ok", "message": "State wiped cleanly"}
