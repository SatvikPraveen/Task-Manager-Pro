#!/usr/bin/env python3
"""
benchmarks/bench_api.py

Closed-loop latency/throughput benchmark for a running API.

Each of ``--concurrency`` workers registers its own user, then loops over a
fixed scenario (create task → list → next → stats → update → get) for
``--iterations`` rounds. Per-endpoint latency percentiles and aggregate
throughput are printed as a Markdown table and optionally written as JSON
(``--json out.json``) so runs can be diffed.

    uvicorn task_manager_pro.api.main:app &            # in another shell
    python benchmarks/bench_api.py --concurrency 8 --iterations 50

Only the standard library plus ``httpx`` are required. Results are for the
*whole stack* (HTTP + auth + ORM + DB), which is what users experience.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from typing import Dict, List

import httpx

Samples = Dict[str, List[float]]


def percentile(values: List[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def worker(base_url: str, iterations: int, samples: Samples, lock: threading.Lock, errors: List[str]) -> None:
    client = httpx.Client(base_url=base_url, timeout=30.0)
    name = f"bench_{uuid.uuid4().hex[:10]}"

    def timed(label: str, method: str, url: str, **kwargs) -> httpx.Response:
        start = time.perf_counter()
        resp = client.request(method, url, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        with lock:
            samples[label].append(elapsed)
            if resp.status_code >= 400:
                errors.append(f"{label}: {resp.status_code} {resp.text[:120]}")
        return resp

    timed("register", "POST", "/api/auth/register", json={"username": name, "password": "benchpass123"})
    token = timed("login", "POST", "/api/auth/login", json={"username": name, "password": "benchpass123"}).json()[
        "access_token"
    ]
    client.headers["Authorization"] = f"Bearer {token}"

    today = date.today()
    for i in range(iterations):
        created = timed(
            "create_task",
            "POST",
            "/api/tasks",
            json={
                "title": f"task {i}",
                "due_date": (today + timedelta(days=i % 30 - 5)).isoformat(),
                "priority": ["low", "medium", "high"][i % 3],
            },
        ).json()
        timed("list_tasks", "GET", "/api/tasks", params={"limit": 20})
        timed("next_tasks", "GET", "/api/tasks/next", params={"limit": 5})
        timed("stats", "GET", "/api/tasks/stats")
        timed("update_task", "PUT", f"/api/tasks/{created['id']}", json={"completed": i % 2 == 0})
        timed("get_task", "GET", f"/api/tasks/{created['id']}")
    client.close()


def run(base_url: str, concurrency: int, iterations: int) -> dict:
    samples: Samples = defaultdict(list)
    errors: List[str] = []
    lock = threading.Lock()

    health = httpx.get(f"{base_url}/health", timeout=10.0)
    health.raise_for_status()

    wall_start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for _ in range(concurrency):
            pool.submit(worker, base_url, iterations, samples, lock, errors)
    wall = time.perf_counter() - wall_start

    total_requests = sum(len(v) for v in samples.values())
    report = {
        "base_url": base_url,
        "concurrency": concurrency,
        "iterations": iterations,
        "wall_seconds": round(wall, 3),
        "total_requests": total_requests,
        "throughput_rps": round(total_requests / wall, 1) if wall else None,
        "errors": errors[:20],
        "endpoints": {
            label: {
                "n": len(values),
                "mean_ms": round(statistics.fmean(values), 2),
                "p50_ms": round(percentile(values, 0.50), 2),
                "p95_ms": round(percentile(values, 0.95), 2),
                "p99_ms": round(percentile(values, 0.99), 2),
                "max_ms": round(max(values), 2),
            }
            for label, values in sorted(samples.items())
        },
    }
    return report


def to_markdown(report: dict) -> str:
    lines = [
        f"**{report['base_url']}** — concurrency {report['concurrency']}, "
        f"{report['iterations']} iterations/worker, {report['total_requests']} requests "
        f"in {report['wall_seconds']} s → **{report['throughput_rps']} req/s**",
        "",
        "| endpoint | n | mean ms | p50 ms | p95 ms | p99 ms | max ms |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, m in report["endpoints"].items():
        lines.append(f"| {label} | {m['n']} | {m['mean_ms']} | {m['p50_ms']} | {m['p95_ms']} | {m['p99_ms']} | {m['max_ms']} |")
    if report["errors"]:
        lines += ["", f"⚠️ {len(report['errors'])} error(s), first few:"] + [f"- {e}" for e in report["errors"][:5]]
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--json", dest="json_path", help="Write the full report to this file")
    args = parser.parse_args(argv)

    report = run(args.base_url, args.concurrency, args.iterations)
    print(to_markdown(report))
    if args.json_path:
        with open(args.json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nJSON written to {args.json_path}")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
