"""Prueba de carga E2E (Fase 6). No se recolecta con pytest.

Uso (dentro de la red de Docker):
    docker compose run --rm etl python tests/load_test.py --base http://frontend --requests 500 --concurrency 50
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import time

import httpx
import psycopg

from app.core.config import settings

ENDPOINTS = [
    ("GET", "/api/v1/crashes/geojson?min_lon=-87.65&min_lat=41.85&max_lon=-87.60&max_lat=41.90&limit=2000", None),
    ("GET", "/api/v1/analytics/kpis", None),
    ("GET", "/api/v1/analytics/hourly-distribution", None),
    ("GET", "/api/v1/tiles/crashes/14/4202/6091.pbf", None),
    ("POST", "/api/v1/predict/segment-risk", {"coordinates": [-87.6298, 41.8781], "posted_speed_limit": 30,
                                              "weather_condition": "RAIN", "lighting_condition": "DARK",
                                              "active_workzone": True}),
]


def db_connections() -> int:
    with psycopg.connect(settings.psycopg_dsn) as conn:
        return conn.execute("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()").fetchone()[0]


async def run(base: str, total: int, concurrency: int) -> dict:
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, list[float]] = {path.split("?")[0]: [] for _, path, _ in ENDPOINTS}
    errors: list[str] = []

    async with httpx.AsyncClient(base_url=base, timeout=30) as client:
        async def one(i: int):
            method, path, body = ENDPOINTS[i % len(ENDPOINTS)]
            if "predict" in path:
                body = {**body, "posted_speed_limit": random.choice([20, 25, 30, 35, 40])}
            async with sem:
                t0 = time.perf_counter()
                try:
                    r = await client.request(method, path, json=body)
                    if r.status_code != 200:
                        errors.append(f"{r.status_code} {path}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{type(exc).__name__} {path}")
                results[path.split("?")[0]].append(time.perf_counter() - t0)

        t0 = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(total)))
        wall = time.perf_counter() - t0

    summary = {
        "requests": total,
        "concurrency": concurrency,
        "wall_s": round(wall, 2),
        "throughput_rps": round(total / wall, 1),
        "errors": len(errors),
        "error_samples": errors[:5],
        "endpoints": {
            k: {"n": len(v), "mean_ms": round(statistics.mean(v) * 1000, 1),
                "p95_ms": round(sorted(v)[int(len(v) * 0.95) - 1] * 1000, 1)}
            for k, v in results.items() if v
        },
    }
    all_lat = [x for v in results.values() for x in v]
    summary["mean_latency_s"] = round(statistics.mean(all_lat), 3)
    summary["gate_mean_latency_lt_2s"] = summary["mean_latency_s"] < 2.0
    return summary


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="http://frontend")
    p.add_argument("--requests", type=int, default=500)
    p.add_argument("--concurrency", type=int, default=50)
    a = p.parse_args()
    before = db_connections()
    summary = asyncio.run(run(a.base, a.requests, a.concurrency))
    time.sleep(2)
    summary["db_connections_before"] = before
    summary["db_connections_after"] = db_connections()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
