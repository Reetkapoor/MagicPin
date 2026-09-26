# Phase 4 — API Runtime & Concurrency

## Implemented

- FastAPI lifespan resets the single-process state at startup.
- `/v1/tick` uses `asyncio.gather` with a bounded `Semaphore(8)`.
- Tick processing has a 14-second internal deadline and a 14.5-second outer timeout guard.
- Individual malformed triggers are isolated so they cannot turn the whole tick into HTTP 500.
- Suppression reservation is atomic and rollback is lock-safe.
- Health uptime uses `time.monotonic()` rather than wall-clock time.
- `/v1/reply` catches unexpected FSM errors and returns a safe `wait` action instead of a 500.
- Existing endpoint aliases remain present and FSM branch ordering remains unchanged.

## Concurrency semantics

Each selected trigger is processed independently. The semaphore caps active trigger work at eight. Suppression keys are reserved before composition, preventing duplicate sends when concurrent tasks target the same weekly suppression key. Failed trigger processing releases its reservation.

## Deferred

- final end-to-end judge score comparison;
- load testing;
- deployment packaging;
- removal/archive of the legacy compatibility surface.

## Verification limitation

The GitHub connector cannot execute the repository's Python test suite, so this checkpoint does not claim a pytest pass.

## Checkpoint 4

**PHASE 4 COMPLETE.**
