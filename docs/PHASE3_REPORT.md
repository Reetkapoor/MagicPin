# Phase 3 — Grounding, Signals, Suppression & Validation

Repository: `Reetkapoor/MagicPin`
Date: 2026-09-26

## Implemented

- `app/facts.py`
  - extracts numeric tokens only from injected category/merchant/trigger/customer context;
  - provides grounded-number checks;
  - exposes a merchant-facts projection.

- `app/signals.py`
  - canonical weights:
    - compliance 1.10
    - performance_dip 1.00
    - seasonal_event 0.95
    - peer_gap 0.90
    - customer_lapse 0.85
    - performance_spike 0.80
    - research_digest 0.60
  - explicitly maps starter-dataset kinds such as `regulation_change`, `perf_dip`, `seasonal_perf_dip`, `competitor_opened`, and lapse variants to those canonical signals;
  - ranks deterministically using signal weight × urgency × novelty × category fit;
  - caps selection at one trigger per merchant and 20 total actions.

- `app/suppression.py`
  - deterministic key format:
    `{trigger_type}:{category}:{merchant_id}:{ISO_YEAR}-W{ISO_WEEK}`
  - derives the week from the request `now`, not wall-clock time.

- `app/playbooks.py`
  - structured playbook metadata for the canonical signal families;
  - deterministic generic fallback.

- `app/validator.py`
  - rejects ungrounded numeric tokens;
  - requires a merchant-name anchor;
  - requires a grounded numeric anchor when numeric facts are available;
  - enforces 80–280 character body length;
  - rejects banned phrases;
  - rejects multiple question marks;
  - requires a structured CTA.

- `app/api.py`
  - tick now uses weighted signal selection;
  - uses request-time suppression keys;
  - gathers allowed numbers exclusively from injected context;
  - performs one deterministic fallback after validation failure;
  - fallback remains merchant-specific and uses an injected numeric anchor when available.

## Important preservation choice

The existing `compose()` dispatcher was not rewritten into a new template engine in Phase 3. This keeps the challenge's known deterministic branches intact while placing the new safety/selection layer around them. Template/playbook migration can therefore be performed later without simultaneously changing ranking or grounding behavior.

## Deferred

- Gemini/LLM integration and caching;
- `asyncio.gather`/Semaphore(8) concurrent trigger processing;
- final load-test and scorecard comparison;
- full catalog-offer semantic enforcement beyond the current validator boundary;
- deployment and cleanup.

## Tests added

- signal weight and one-per-merchant selection;
- weekly suppression-key determinism;
- grounded-number rejection;
- grounded-number acceptance.

The repository connector does not execute pytest, so no test-pass claim is made here.

## Checkpoint 3

**PHASE 3 IMPLEMENTED.**
