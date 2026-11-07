"""Rejilla de riesgo vial (celdas de 500 m) y métricas del modelo."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pyproj import Transformer
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import OlapUnavailableError
from app.core.http_cache import TTLCache, cached_bytes_response, dumps, etag_for
from app.core.severity import GRID_SIZE_FT
from app.services.olap import duckdb_engine

router = APIRouter()

_to_wgs84 = Transformer.from_crs(3435, 4326, always_xy=True)


def _cell_polygon(gx: int, gy: int) -> list[list[list[float]]]:
    x0, y0 = gx * GRID_SIZE_FT, gy * GRID_SIZE_FT
    x1, y1 = x0 + GRID_SIZE_FT, y0 + GRID_SIZE_FT
    xs, ys = _to_wgs84.transform([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0])
    return [[[round(x, 6), round(y, 6)] for x, y in zip(xs, ys)]]


# Respuestas ya serializadas (bytes + ETag) por versión del archivo Gold: FastAPI ya
# no recorre miles de polígonos con jsonable_encoder en cada petición.
_bytes_cache = TTLCache(maxsize=48, ttl=3600)

NOT_TRAINED = "Aún no se ha entrenado el modelo por tramo"


def _gold_version() -> float:
    path = Path(settings.DUCKDB_PATH)
    if not path.exists():
        raise OlapUnavailableError("Capa Gold (DuckDB) no disponible: ejecute el pipeline ETL", None)
    return path.stat().st_mtime


def _cached(key: tuple, build) -> tuple[bytes, str]:
    hit = _bytes_cache.get(key)
    if hit is None:
        body = dumps(build())
        hit = (body, etag_for(body))
        _bytes_cache.set(key, hit)
    return hit


def _require_segments() -> None:
    if not duckdb_engine.table_exists("gold_segment_risk"):
        raise HTTPException(status_code=404, detail=NOT_TRAINED)


def _grid_geojson(min_crashes: int) -> dict:
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
async def risk_grid(request: Request, min_crashes: int = Query(10, ge=1, le=1000)) -> Response:
    def build() -> tuple[bytes, str]:
        return _cached(("grid", min_crashes, _gold_version()), lambda: _grid_geojson(min_crashes))

    body, etag = await run_in_threadpool(build)
    return cached_bytes_response(request, body, etag, media_type="application/geo+json", max_age=600)


@lru_cache(maxsize=4)
def _read_report(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


async def _report(name: str, missing: str) -> dict:
    path = Path(settings.MODEL_PATH).with_name(name)
    if not path.exists():
        raise HTTPException(status_code=404, detail=missing)
    return await run_in_threadpool(_read_report, str(path), path.stat().st_mtime)


@router.get("/model-metrics", summary="Métricas de evaluación del modelo entrenado")
async def model_metrics() -> dict:
    report = await _report("model_report.json", "Aún no hay un modelo entrenado")
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
        # Claves añadidas por el informe del modelo v2 (None si el informe es anterior)
        "test_decision": m.get("test_decision"),
        "calibration_critical": {k: v for k, v in (m.get("calibration_critical") or {}).items()
                                 if k != "reliability"} or None,
        "windows": report.get("windows"),
        "ablation_pre_crash_only": report.get("ablation_pre_crash_only"),
        "selection_metric": report.get("selection_metric"),
    }


SEGMENT_COLUMNS = ("segment_id, lat, lon, crashes, injury_crashes, severe_crashes, fatalities, ped_crashes, "
                   "bike_crashes, mean_speed, mean_aadt, p_alto, p_medio, p_bajo, risk_class, priority_rank, priority_pct")


def _segments(limit: int, min_class: int) -> dict:
    _require_segments()
    rows = duckdb_engine.query(
        f"SELECT {SEGMENT_COLUMNS} FROM gold_segment_risk WHERE risk_class >= ? ORDER BY priority_rank LIMIT ?",
        [min_class, limit])
    return {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "id": r["segment_id"],
             "geometry": {"type": "Point", "coordinates": [round(r["lon"], 6), round(r["lat"], 6)]},
             "properties": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                            if k not in ("lat", "lon")}}
            for r in rows if r["lat"] is not None
        ],
    }


@router.get("/segments", summary="Tramos viales (cuadras) con riesgo anticipado para los próximos 12 meses (GeoJSON)")
async def risk_segments(
    request: Request,
    limit: int = Query(5_000, ge=1, le=25_000, description="Tramos más prioritarios a devolver"),
    min_class: int = Query(0, ge=0, le=2, description="Clase mínima: 0 Bajo, 1 Medio, 2 Alto"),
) -> Response:
    def build() -> tuple[bytes, str]:
        return _cached(("segments", limit, min_class, _gold_version()), lambda: _segments(limit, min_class))

    body, etag = await run_in_threadpool(build)
    return cached_bytes_response(request, body, etag, media_type="application/geo+json", max_age=600)


def _segment_distribution(size: int) -> dict:
    _require_segments()
    n = duckdb_engine.query("SELECT count(*) AS n FROM gold_segment_risk")[0]["n"]
    step = max(1, n // size)
    # Muestra sistemática por rango: conserva la forma de la distribución completa
    rows = duckdb_engine.query(
        "SELECT p_alto FROM gold_segment_risk WHERE priority_rank % ? = 0 ORDER BY priority_rank", [step])
    return {"segments_total": int(n), "step": step, "p_alto": [round(float(r["p_alto"]), 4) for r in rows]}


@router.get("/segment-distribution", summary="Muestra de P(riesgo Alto) de todas las cuadras (para comparar un tramo)")
async def segment_distribution(request: Request, size: int = Query(1_500, ge=100, le=5_000)) -> Response:
    def build() -> tuple[bytes, str]:
        return _cached(("distribution", size, _gold_version()), lambda: _segment_distribution(size))

    body, etag = await run_in_threadpool(build)
    return cached_bytes_response(request, body, etag, max_age=600)


def _segment_known(segment_id: str) -> bool:
    _require_segments()
    rows = duckdb_engine.query("SELECT count(*) AS n FROM gold_segment_risk WHERE segment_id = ?", [segment_id])
    return bool(rows[0]["n"])


@router.get("/segment-explain", summary="Probabilidad de un tramo y variables que la explican (modelo por tramo)")
async def segment_explain(segment_id: str = Query(..., min_length=3, max_length=120)) -> dict:
    from app.ml.segment_explain import explain_segment, model_mtime

    try:
        mtime = model_mtime()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=NOT_TRAINED) from None
    # Comprobación barata en la capa Gold antes de recalcular variables en PostGIS
    if not await run_in_threadpool(_segment_known, segment_id):
        raise HTTPException(status_code=404, detail="Tramo no encontrado entre los tramos con riesgo publicado")
    try:
        result = await run_in_threadpool(explain_segment, segment_id, mtime)
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from None
    if result is None:
        raise HTTPException(status_code=404, detail="Tramo sin siniestros en la ventana de historia")
    return result


@router.get("/segment-model-metrics", summary="Métricas del modelo de riesgo por tramo vial")
async def segment_model_metrics() -> dict:
    r = await _report("segment_model_report.json", NOT_TRAINED)
    models = r.get("models", {})
    winner = r.get("winner")
    return {
        "winner": winner,
        "selection_metric": r.get("selection_metric"),
        "unit": r.get("unit"),
        "windows": r.get("windows"),
        "n_train": r.get("n_train"),
        "n_test": r.get("n_test"),
        "class_distribution_test": r.get("class_distribution_test"),
        "comparison": {k: {**v.get("temporal_test", {}),
                           "spatial_cv_auc": v.get("spatial_cv", {}).get("auc_mean"),
                           "spatial_cv_variation": v.get("spatial_cv", {}).get("auc_cv_variation")}
                       for k, v in models.items()},
        "confusion_matrix": models.get(winner, {}).get("confusion_matrix"),
        "forecast": r.get("forecast"),
        "baselines": r.get("baselines"),
        "bootstrap_top10_capture": r.get("bootstrap_top10_capture"),
        "winner_vs_best_baseline": r.get("winner_vs_best_baseline"),
        "selection": r.get("selection"),
        "anchor_date": r.get("anchor_date"),
    }
