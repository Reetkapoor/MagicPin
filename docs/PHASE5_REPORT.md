# Phase 5 — Evaluation & Load-Test Harness

## Implemented
- Added `scripts/phase5_scorecard.py` to compare the migrated app against the preserved baseline commit `ec9c2d114991d3862120a739e28af0bffd98d153`.
- Added `scripts/load_test.py` for concurrent HTTP health checks.
- Added `requirements.txt`.
- Added GitHub Actions verification for tests, scorecard, and HTTP load testing.

## Verification result

GitHub Actions run `36256657934` completed successfully.

### Pytest
- **24 passed**
- 1 existing Starlette/httpx deprecation warning.

### Baseline vs migrated scorecard
Using the seed dataset (the local judge's dataset):
- Categories: 5
- Merchants: 10
- Customers: 15
- Triggers: 25
- Baseline actions: 10
- Migrated actions: 10
- Baseline schema-complete actions: 10/10
- Migrated schema-complete actions: 10/10
- Baseline messages within 80–280 chars: 4/10
- Migrated messages within 80–280 chars: 10/10
- Baseline merchant-name presence: 5/10
- Migrated merchant-name presence: 10/10
- CTA present: 10/10 for both
- Determinism: **true**

### HTTP load test
- Requests: 100
- Workers: 8
- Successful: 100
- Failed: 0
- p95 latency: **5.1 ms**
- Max latency: **8.7 ms**

## Fixes made during verification
- Grounding validation now reports fabricated numeric tokens before secondary formatting failures.
- Fractional injected percentages (for example `-0.12`) are normalized for rendered percentage grounding.
- Restored the required Saturday IPL `-12%` behavior while keeping the fact in trigger context.
- Reworked the corporate-thali planning message to remain actionable without qualifying-question language and within the outbound length limit.
- Fixed the Phase 5 scorecard's repository import path, customer seeding, and baseline-commit fetch.
- Added the HTTP load-test step to the verification workflow.

## Checkpoint 5
**PHASE 5 VERIFIED SUCCESSFULLY.**

Phase 6 may proceed to deployment packaging, README completion, and legacy-surface archival/removal, subject to the Phase 6 gate checks.
