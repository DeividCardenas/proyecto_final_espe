"""Inferencia de riesgo vial en vivo para un tramo / punto de Chicago."""
from __future__ import annotations

import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from starlette.concurrency import run_in_threadpool

from app.core.database import get_pool
from app.core.severity import GRID_SIZE_FT
from app.schemas.prediction import SegmentRiskRequest, SegmentRiskResponse

router = APIRouter()

CHICAGO_TZ = ZoneInfo("America/Chicago")
AADT_RADIUS_FT = 500 * 3.2808333

# Contexto espacial del punto: aforo AADT más cercano (KNN) y densidad histórica
# de la celda de 500 m, ambos resueltos con índices GiST en EPSG:3435.
CONTEXT_SQL = f"""
WITH pt AS (SELECT ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 3435) AS g),
cell AS (
    SELECT floor(ST_X(g) / {GRID_SIZE_FT}) * {GRID_SIZE_FT} AS x0,
           floor(ST_Y(g) / {GRID_SIZE_FT}) * {GRID_SIZE_FT} AS y0 FROM pt
)
SELECT
    (SELECT json_build_object('volume', t.total_passing_vehicle_volume, 'dist_ft', t.geom_3435 <-> pt.g,
                              'street', t.street)
     FROM silver_traffic_counts t, pt ORDER BY t.geom_3435 <-> pt.g LIMIT 1)::text AS aadt,
    (SELECT round(avg(total_passing_vehicle_volume)) FROM silver_traffic_counts) AS aadt_mean,
    (SELECT count(*) FROM silver_crashes c, cell
      WHERE c.geom_3435 && ST_MakeEnvelope(cell.x0, cell.y0, cell.x0 + {GRID_SIZE_FT}, cell.y0 + {GRID_SIZE_FT}, 3435)
    ) AS cell_crashes
"""


@router.post("/segment-risk", response_model=SegmentRiskResponse,
             summary="Predice el nivel de riesgo de un tramo vial")
async def segment_risk(req: SegmentRiskRequest, request: Request) -> SegmentRiskResponse:
    t0 = time.perf_counter()
    lon, lat = req.coordinates
    async with get_pool().acquire() as conn:
        ctx = await conn.fetchrow(CONTEXT_SQL, lon, lat)
    aadt = json.loads(ctx["aadt"]) if ctx["aadt"] else None
    near = aadt is not None and aadt["dist_ft"] <= AADT_RADIUS_FT
    years = float(getattr(request.app.state, "data_years", 1.0))
    when = (req.when.astimezone(CHICAGO_TZ) if req.when and req.when.tzinfo else req.when) or datetime.now(CHICAGO_TZ)

    raw = {
        "crash_date": when.replace(tzinfo=None),
        "posted_speed_limit": req.posted_speed_limit,
        "weather_condition": req.weather_condition,
        "lighting_condition": req.lighting_condition,
        "roadway_surface_cond": req.roadway_surface_cond or (
            "WET" if req.weather_condition == "RAIN" else "SNOW_ICE" if req.weather_condition == "SNOW" else "DRY"),
        "trafficway_type": req.trafficway_type,
        "traffic_control_device": req.traffic_control_device,
        "intersection_related_i": req.intersection_related,
        "first_crash_type": req.first_crash_type,
        "has_pedestrian": req.first_crash_type == "PEDESTRIAN",
        "has_cyclist": req.first_crash_type == "PEDALCYCLIST",
        "num_units": 1 if req.first_crash_type in ("FIXED OBJECT", "OVERTURNED", "OTHER NONCOLLISION") else 2,
        "aadt_volume": aadt["volume"] if near else ctx["aadt_mean"],
        "aadt_imputed": not near,
        "active_workzone": req.active_workzone,
        "grid_density": ctx["cell_crashes"] / years,
        "latitude": lat,
        "longitude": lon,
    }
    predictor = request.app.state.predictor
    result = await run_in_threadpool(predictor.predict, raw)
    return SegmentRiskResponse(
        **result,
        context={
            "evaluated_at": when.isoformat(),
            "aadt_volume": raw["aadt_volume"],
            "aadt_station_distance_m": round(aadt["dist_ft"] / 3.2808333, 1) if aadt else None,
            "aadt_imputed": raw["aadt_imputed"],
            "cell_crashes_per_year": round(raw["grid_density"], 2),
            "roadway_surface_cond": raw["roadway_surface_cond"],
        },
        model={
            "mode": "ml" if predictor.loaded else "heuristic_fallback",
            "algorithm": predictor.meta.get("algorithm"),
            "trained_at": predictor.meta.get("trained_at"),
        },
        inference_ms=round((time.perf_counter() - t0) * 1000, 2),
    )
