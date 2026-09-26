# Phase 1 Reconciliation Report

Repository: `Reetkapoor/MagicPin`
Audit date: 2026-09-26
Baseline commit: `ec9c2d114991d3862120a739e28af0bffd98d153` (single commit, no parent)

## 1. Authoritative contract reviewed

Audited:
- `judge_simulator.py`
- `challenge-testing-brief.md`
- `challenge-brief.md`
- `examples/api-call-examples.md`
- `bot.py`
- `test_bot.py`
- `submission.jsonl`
- dataset/expanded repository tree and `expanded/test_pairs.json`

The challenge brief defines the five HTTP endpoints and five scoring dimensions. The local `judge_simulator.py` is the executable local harness and takes precedence where its implementation differs from prose.

### Wire contract

| Endpoint | Method | Request | Success response |
|---|---|---|---|
| `/v1/context` | POST | `scope`, `context_id`, `version`, `payload`, `delivered_at` | 200: `accepted=true`, `ack_id`, `stored_at` |
| `/v1/context` | POST | same id, version <= stored | 409: `accepted=false`, `reason=stale_version`, `current_version` |
| `/v1/tick` | POST | `now`, `available_triggers[]` | 200: `actions[]`; empty is valid |
| `/v1/reply` | POST | `conversation_id`, optional merchant/customer ids, `from_role`, `message`, `received_at`, `turn_number` | 200: action `send|wait|end` |
| `/v1/healthz` | GET | none | 200: `status`, `uptime_seconds`, `contexts_loaded` |
| `/v1/metadata` | GET | none | 200: team/model/approach/contact/version/submitted_at |

Tick actions require `conversation_id`, `merchant_id`, `customer_id`, `send_as`, `trigger_id`, `template_name`, `template_params`, `body`, `cta`, `suppression_key`, and `rationale`.

### Operational limits

Testing brief:
- max judge request rate: 10 req/s
- per-call timeout: 30s
- context payload cap: 500 KB
- max tick actions: 20
- 3 consecutive health failures disqualify
- 60 simulated minutes

The executable local simulator uses shorter client-side timeouts: healthz/metadata 5s, context 10s, tick 15s, reply 15s.

## 2. Scoring contract

Five dimensions, 0-10 each:
1. Specificity — concrete, verifiable context facts.
2. Category fit — vertical-specific voice/vocabulary.
3. Merchant fit — this merchant's state, offers, language, history.
4. Trigger relevance / decision quality — clear why-now connection.
5. Engagement compulsion — curiosity, social proof, loss aversion, effort externalization, clear CTA.

Local judge penalty instructions:
- fabricated data: -2
- internal jargon exposed to merchant: -1

Total = five dimensions minus penalties, floored at zero.

## 3. Baseline bot audit

`bot.py` is a deterministic, zero-runtime-LLM FastAPI implementation with:
- 26 composition condition families (including the combined wedding/bridal condition);
- deterministic template output with all required tick-action fields;
- reply FSM precedence: auto-reply -> hostile/opt-out -> commitment -> off-topic -> affirmative/question -> default;
- in-memory contexts/conversations/suppressions/active conversations/opt-outs;
- all five `/v1/*` endpoints plus unprefixed aliases;
- a 20-action tick cap and one action per merchant per tick;
- URL/taboo sanitization.

### Mismatches

| ID | Finding | Current bot | Required treatment |
|---|---|---|---|
| P1-01 | Required request fields | `delivered_at`, `now`, `received_at` optional | Make protocol-required fields required |
| P1-02 | Inbound extras | Pydantic defaults to ignore unknown fields | Use `ConfigDict(extra="allow")` |
| P1-03 | Outbound models | Plain dicts | Add strict Pydantic response models |
| P1-04 | Context size | No 500 KB check | Reject >500 KB deterministically |
| P1-05 | Store | Plain dicts, no lock/index/snapshot | Implement copy-on-write lock + MappingProxy snapshots + secondary indexes |
| P1-06 | Versioning | <= current returns 409 stale_version | Preserve this wire behavior; internal write path can be a no-op |
| P1-07 | Tick ranking | Urgency-only descending | Add weighted type/urgency/magnitude/novelty/category-fit scorer, deterministic tie-break |
| P1-08 | Suppression | Uses trigger-provided key | Add deterministic key derived from request `now` per directive |
| P1-09 | Wall clock | tick/reply conversation timestamps use `datetime.now(timezone.utc)` | Thread simulated request time through all tick/reply state and suppression calculations |
| P1-10 | Context timestamp | `stored_at` uses wall clock | Define deterministic timestamp policy without changing wire shape |
| P1-11 | Grounding | Sanitizer only strips URLs/taboos | Add facts extraction + numeric/date/price/catalog grounding hard-gate |
| P1-12 | Hardcoded fallbacks | Several templates contain default facts | Validator must reject unsupported claims and fall back safely |
| P1-13 | Playbooks | Vertical rules embedded inline | Extract five structured playbooks |
| P1-14 | LLM | None | Optional; skip unless API key is intentionally available |
| P1-15 | Tick concurrency | Sequential composition | Add gather + Semaphore(8) + deadline in Phase 4 |
| P1-16 | Healthz | Scans mutable state every request | Use lock-free snapshot/counters and keep it disk/LLM-free |
| P1-17 | Malformed input | Pydantic validation may return 422 | Reconcile explicit 400 protocol error handling |
| P1-18 | Local judge data | `judge_simulator.py` loads only `dataset/` | Preserve this for local baseline; separately validate expanded artifacts |
| P1-19 | Dataset discrepancy | seed = 10 merchants/15 customers/25 triggers | Expanded artifact is complete at 50/200/100; do not regenerate either set blindly |
| P1-20 | Submission | 30 complete JSONL lines | Already valid; no regeneration |
| P1-21 | Repetition | No explicit body-repeat hard gate | Add repetition/suppression support |
| P1-22 | Customer templates | Some contain fixed defaults | Ground customer claims against injected contexts |

## 4. Determinism audit

The known bug is confirmed. There are four wall-clock timestamp sites in `bot.py`:
- tick conversation timestamp;
- reply inbound turn timestamp;
- reply outbound turn timestamp;
- context `stored_at`.

`TickRequest.now` is optional and currently unused for ranking/suppression/time calculations.

Migration requirement:
- require tick `now`;
- pass simulated time into ranking, suppression, and conversation state;
- never use system wall clock for simulated-event timestamps;
- add a regression test that demonstrates fixed input produces fixed simulated output and would fail against the old implementation.

## 5. Dataset and submission audit

Expanded repository tree:
- 5 categories
- 50 merchants
- 200 customers
- 100 triggers
- 30 canonical pairs

`expanded/test_pairs.json`: exactly 30 pairs.

Seed data used by the local judge:
- 5 categories
- 10 merchants
- 15 customers
- 25 triggers

This is why the current `test_bot.py` expects 5/10/15/25. The expanded dataset is complete at the challenge's 50/200/100 scale. The local judge's seed-vs-expanded discrepancy is documented rather than “fixed” by regeneration.

`submission.jsonl`:
- 30 non-empty lines
- all parse as JSON
- all have non-empty `test_id`, `body`, `cta`, `send_as`, `suppression_key`, `rationale`
- IDs exactly T01-T30
- no regeneration required

## 6. test_bot.py disposition

10 existing tests:

| Test | Destination |
|---|---|
| `test_healthz_and_metadata` | `tests/test_api.py` |
| `test_context_push_and_idempotency` | API assertions in `tests/test_api.py`; lower-level version tests in `tests/test_store.py` |
| `test_full_dataset_tick_and_suppression` | API lifecycle + signal/suppression unit tests |
| `test_ipl_saturday_contrarian_behavior` | `tests/test_composer.py` |
| `test_active_planning_no_qualifying` | `tests/test_composer.py` |
| `test_auto_reply_turn_sequence` | `tests/test_reply_fsm.py` |
| `test_intent_transition_action_mode` | `tests/test_reply_fsm.py` |
| `test_hostile_opt_out` | `tests/test_reply_fsm.py` |
| `test_off_topic_curveball` | `tests/test_reply_fsm.py` |
| `test_canonical_30_pairs` | `tests/test_composer.py` plus an explicit evaluation/submission script |

Disposition: **move/refactor, do not discard**. Preserve useful assertions. Remove the pytest side effect that writes `submission.jsonl`; generation belongs in an explicit evaluation script.

## 7. Checkpoint 1

**RECONCILIATION COMPLETE.**

No application code was changed during Phase 1.

The migration baseline is `bot.py` as-is. Preserve its successful wire behavior and composition/FSM branches, while fixing only the verified protocol/determinism/grounding/store/ranking/concurrency requirements documented above.
