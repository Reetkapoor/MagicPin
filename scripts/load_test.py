#!/usr/bin/env python3
"""Simple Phase 5 load test against a running Vera HTTP server.

Usage: python scripts/load_test.py --base-url http://127.0.0.1:8000
"""
from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import request


def call(base_url, path, payload=None, timeout=15):
    data = None
    headers = {}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = request.Request(base_url.rstrip("/") + path, data=data, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return resp.status, (time.perf_counter() - started) * 1000
    except Exception:
        return 0, (time.perf_counter() - started) * 1000


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--requests", type=int, default=100)
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(call, args.base_url, "/v1/healthz", None, 5)
            for _ in range(args.requests)
        ]
        results = [f.result() for f in as_completed(futures)]

    statuses = [s for s, _ in results]
    latencies = sorted(lat for _, lat in results)
    ok = sum(s == 200 for s in statuses)
    p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0

    print(f"requests={len(results)} ok={ok} failed={len(results)-ok}")
    print(f"p95_ms={p95:.1f} max_ms={max(latencies, default=0):.1f}")

    if ok != len(results):
        return 1
    if p95 > 5000:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
