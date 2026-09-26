# Phase 2 — Decomposition & Baseline-Preservation Report

Repository: `Reetkapoor/MagicPin`
Date: 2026-09-26
Baseline: Checkpoint 1 commit `7e688d3377a16701fab752b9b090dcaa64719d06`

## Completed

- Added `app/` package with:
  - `app/main.py` — deployment/import entrypoint exposing the FastAPI app.
  - `app/api.py` — HTTP routes and protocol handling.
  - `app/schemas.py` — inbound models with `extra="allow"` and strict outbound response models.
  - `app/store.py` — single-process store with write locking, version checks, scope indexes, deep-copy writes, and immutable `MappingProxyType` snapshots.
  - `app/composer.py` — existing deterministic composer and reply FSM moved without rewriting their branch logic.
  - `app/config.py` — protocol/runtime constants.
  - `app/logging_setup.py` — logging bootstrap.
- Replaced `bot.py` with a compatibility facade so the historical `bot.app`, `bot.state`, `bot.compose`, and `bot.handle_reply` imports remain valid.
- Preserved the unprefixed and `/v1/*` endpoint aliases.
- Preserved the existing 20-action tick cap and suppression behavior for this phase.
- Added a deterministic 500 KB context-payload guard.
- Removed simulated-event dependence on wall-clock time in the migrated tick/reply/context paths; request timestamps are used when supplied, with deterministic epoch fallback for legacy callers.
- Added focused regression tests under `tests/` for store versioning/snapshots, API behavior, composer behavior, and reply FSM behavior.
- Added API tests for the 500 KB cap and request-time propagation.

## Deliberately deferred

These remain for later phases and were not mixed into the decomposition:

- weighted trigger scoring and novelty/category-fit ranking;
- deterministic suppression-key redesign based on request `now`;
- full facts extraction / allowed-number grounding validator;
- structured playbooks/templates migration;
- optional Gemini integration;
- `asyncio.gather` + Semaphore(8) tick concurrency and deadline;
- final healthz lock-free snapshot optimization;
- deployment files, README, load testing, and final baseline-vs-migrated scorecard.

## Compatibility notes

The inbound timestamp fields remain optional at this intermediate checkpoint because the existing challenge tests and legacy callers omit them. The API uses deterministic fallbacks rather than system time. Required-field enforcement can be tightened once the migrated test fixtures and protocol harness are updated together.

The local judge's seed dataset discrepancy remains unchanged, as documented in `docs/PROTOCOL_NOTES.md`.

## Verification

Static repository verification confirms the migrated composer is 759 lines and the API/store/schema modules are present. The existing `bot.py` is now a 15-line compatibility facade.

The connector environment does not execute the repository's Python test suite, so this checkpoint does not claim a local `pytest` pass. The new regression tests are committed for execution in the repository's normal Python environment.

## Checkpoint 2 status

**DECOMPOSITION COMPLETE.**

No Phase 3 signal/grounding logic has been introduced.
