# Vera Merchant AI Assistant

A deterministic, stateful FastAPI implementation for the magicpin AI Challenge.

## Architecture

The runtime entrypoint is:

```
app.main:app
```

The application is split into focused modules:

- `app/api.py` — HTTP endpoints and fail-safe request handling
- `app/schemas.py` — strict outbound and permissive inbound protocol models
- `app/store.py` — single-process in-memory state, versioning, snapshots and suppression
- `app/composer.py` — deterministic composition and reply FSM
- `app/facts.py` — grounding/allowed-number extraction
- `app/signals.py` — weighted trigger prioritisation
- `app/suppression.py` — deterministic weekly suppression keys
- `app/playbooks.py` — trigger-family playbooks
- `app/validator.py` — outbound grounding and format gates
- `app/config.py` — operational limits

No runtime LLM or external API is required.

## Local demo UI

The repository includes a lightweight browser UI served directly by FastAPI. It exercises the real `/v1/context`, `/v1/tick`, `/v1/reply`, and `/v1/teardown` endpoints.

After starting the server, open:

```text
http://127.0.0.1:8000/
```

The UI includes editable merchant/category/trigger JSON, one-click demo data, trigger execution, generated messages, CTA and decision details, merchant reply simulation, and state reset. Swagger remains available at `/docs`.

## API

The challenge endpoints are available under `/v1`:

- `GET /v1/healthz`
- `GET /v1/metadata`
- `POST /v1/context`
- `POST /v1/tick`
- `POST /v1/reply`
- `POST /v1/teardown`

Unprefixed aliases are also retained for compatibility.

### Run locally

Python 3.11+ is recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/v1/healthz
```

## Tests and verification

Run the migrated test suite:

```bash
python -m pytest -q
```

Run the baseline-vs-migrated scorecard:

```bash
python scripts/phase5_scorecard.py
```

Run the HTTP load test against a running server:

```bash
python scripts/load_test.py --base-url http://127.0.0.1:8000 --requests 100 --workers 8
```

GitHub Actions runs all three verification stages.

The verified Phase 5 run recorded 24 passing tests, deterministic output, 100/100 successful health requests, and 5.1 ms p95 latency.

## Deployment

### Render

The repository includes `render.yaml`. Render should run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The service is intentionally stateless across restarts except for its in-memory runtime state; challenge contexts are pushed through the API.

### Docker

Build and run:

```bash
docker build -t vera-merchant-ai .
docker run --rm -p 8000:8000 vera-merchant-ai
```

## Data and challenge artifacts

- `dataset/` is the seed dataset used by the local judge.
- `expanded/` contains the expanded 50-merchant / 200-customer / 100-trigger artifacts.
- `submission.jsonl` contains the 30 canonical submission examples.
- `challenge-brief.md`, `challenge-testing-brief.md`, and `examples/` are retained as challenge reference material.
- Phase reports under `docs/` document the migration decisions and verification gates.

## Baseline preservation

The original one-commit implementation was verified before cleanup and is archived at:

`archive/baseline/bot.py`

Baseline commit:

`ec9c2d114991d3862120a739e28af0bffd98d153`

The runtime no longer imports the old monolithic `bot.py`; use `app.main:app`.
