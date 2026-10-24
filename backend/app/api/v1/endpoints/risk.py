"""Rejilla de riesgo vial (celdas de 500 m) y métricas del modelo."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pyproj import Transformer
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.severity import GRID_SIZE_FT
from app.services.olap import duckdb_engine

router = APIRouter()

_to_wgs84 = Transformer.from_crs(3435, 4326, always_xy=True)


def _cell_polygon(gx: int, gy: int) -> list[list[list[float]]]:
    x0, y0 = gx * GRID_SIZE_FT, gy * GRID_SIZE_FT
    x1, y1 = x0 + GRID_SIZE_FT, y0 + GRID_SIZE_FT
    xs, ys = _to_wgs84.transform([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0])
    return [[[round(x, 6), round(y, 6)] for x, y in zip(xs, ys)]]


@lru_cache(maxsize=4)
def _grid_geojson(min_crashes: int, mtime: float) -> dict:
    tables = {r["table_name"] for r in duckdb_engine.query("SELECT table_name FROM information_schema.tables")}
    if "gold_grid_ml" in tables:
        rows = duckdb_engine.query(
            "SELECT m.grid_x, m.grid_y, m.crashes, m.mean_p_critical AS risk, m.observed_critical_rate, "
            "g.fatalities, g.mean_aadt FROM gold_grid_ml m LEFT JOIN gold_grid g USING (grid_x, grid_y) "
            "WHERE m.crashes >= ?", [min_crashes])
        source = "ml"
    else:
        rows = duckdb_engine.query(
            "SELECT grid_x, grid_y, crashes, critical_rate AS risk, critical_rate AS observed_critical_rate, "
            "fatalities, mean_aadt FROM gold_grid WHERE crashes >= ?", [min_crashes])
        source = "empirical"
    risks = sorted(r["risk"] for r in rows)
    q = lambda p: risks[int(p * (len(risks) - 1))] if risks else 0  # noqa: E731
    breaks = {"p50": q(0.5), "p80": q(0.8), "p95": q(0.95)}
    feats = []
    for r in rows:
        level = 2 if r["risk"] >= breaks["p80"] else 1 if r["risk"] >= breaks["p50"] else 0
        feats.append({
            "type": "Feature",
            "id": f"{r['grid_x']}_{r['grid_y']}",
            "geometry": {"type": "Polygon", "coordinates": _cell_polygon(r["grid_x"], r["grid_y"])},
            "properties": {
                "risk": round(float(r["risk"]), 5),
                "risk_level": level,
                "crashes": int(r["crashes"]),
                "observed_critical_rate": round(float(r["observed_critical_rate"] or 0), 5),
                "fatalities": int(r["fatalities"] or 0),
                "mean_aadt": round(float(r["mean_aadt"])) if r["mean_aadt"] is not None else None,
            },
        })
    return {"type": "FeatureCollection", "source": source, "breaks": breaks, "features": feats}


@router.get("/grid", summary="Rejilla de 500 m con riesgo crítico medio predicho (GeoJSON)")
async def risk_grid(min_crashes: int = Query(10, ge=1, le=1000)) -> dict:
    path = Path(settings.DUCKDB_PATH)
    if not path.exists():
        raise HTTPException(status_code=503, detail="Capa Gold (DuckDB) no disponible")
    return await run_in_threadpool(_grid_geojson, min_crashes, path.stat().st_mtime)


@router.get("/model-metrics", summary="Métricas de evaluación del modelo entrenado")
async def model_metrics() -> dict:
    path = Path(settings.MODEL_PATH).with_name("model_report.json")
    if not path.exists():
        raise HTTPException(status_code=404, detail="Aún no hay un modelo entrenado")
    report = json.loads(path.read_text(encoding="utf-8"))
    winner = report.get("winner")
    m = report.get("models", {}).get(winner, {})
    return {
        "winner": winner,
        "trained_at": report.get("trained_at"),
        "n_rows": report.get("n_rows"),
        "class_distribution": report.get("class_distribution"),
        "gates": report.get("gates"),
        "thresholds_required": report.get("thresholds_required"),
        "test": m.get("test_argmax"),
        "test_f1_threshold": m.get("test_f1_threshold"),
        "cv": m.get("cv"),
        "confusion_matrix": m.get("confusion_matrix"),
        "feature_importance": m.get("feature_importance"),
        "comparison": {a: v.get("test_argmax") for a, v in report.get("models", {}).items()},
        "artifact": report.get("artifact"),
    }
