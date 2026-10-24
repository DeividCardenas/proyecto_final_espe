"""Teselas vectoriales Mapbox Vector Tile (ST_AsMVT) para renderizado masivo en MapLibre.

* zoom >= 13: un punto por siniestro con sus atributos.
* zoom < 13: agregación por celda de pantalla (4-8 px), hora y severidad. Al conservar
  ``hour`` y ``severity`` como atributos, el cliente puede seguir filtrando en GPU
  (``map.setFilter``) sin pedir nuevas teselas; ``count`` sirve de peso del heatmap.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, Response

from app.core.database import get_pool

router = APIRouter()

EXTENT = 4096
DETAIL_ZOOM = 13

POINTS_SQL = """
WITH env AS (SELECT ST_TileEnvelope($1, $2, $3) AS e3857),
mvt AS (
    SELECT ST_AsMVTGeom(ST_Transform(c.geom, 3857), env.e3857, {extent}, 64, true) AS geom,
           c.crash_record_id AS id, c.severity, c.crash_hour AS hour, c.crash_day_of_week AS dow,
           c.injuries_total AS injuries, c.injuries_fatal AS fatal, c.active_workzone AS workzone,
           1 AS count
    FROM silver_crashes c, env
    WHERE c.geom && ST_Transform(env.e3857, 4326) {filters}
)
SELECT ST_AsMVT(mvt, 'crashes', {extent}, 'geom') FROM mvt WHERE geom IS NOT NULL
"""

AGG_SQL = """
WITH env AS (SELECT ST_TileEnvelope($1, $2, $3) AS e3857),
pts AS (
    SELECT ST_SnapToGrid(ST_AsMVTGeom(ST_Transform(c.geom, 3857), env.e3857, {extent}, 64, true), {snap}) AS g,
           c.severity, c.crash_hour, c.injuries_fatal
    FROM silver_crashes c, env
    WHERE c.geom && ST_Transform(env.e3857, 4326) {filters}
),
mvt AS (
    SELECT g AS geom, severity, crash_hour AS hour, count(*)::int AS count, sum(injuries_fatal)::int AS fatal
    FROM pts WHERE g IS NOT NULL
    GROUP BY g, severity, crash_hour
)
SELECT ST_AsMVT(mvt, 'crashes', {extent}, 'geom') FROM mvt
"""


@router.get("/crashes/{z}/{x}/{y}.pbf", summary="Tesela vectorial MVT de siniestros",
            response_class=Response)
async def crash_tile(
    z: int = Path(..., ge=0, le=22),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
) -> Response:
    if x >= 2 ** z or y >= 2 ** z:
        raise HTTPException(status_code=404, detail="Tesela fuera de rango")
    params: list = [z, x, y]
    filters = ""
    if start_date:
        params.append(start_date)
        filters += f" AND c.crash_date >= ${len(params)}"
    if end_date:
        params.append(end_date)
        filters += f" AND c.crash_date < (${len(params)}::date + 1)"
    template = POINTS_SQL if z >= DETAIL_ZOOM else AGG_SQL
    snap = 32 if z <= 10 else 16  # celda de agregación en unidades de tesela
    sql = template.format(extent=EXTENT, filters=filters, snap=snap)
    async with get_pool().acquire() as conn:
        tile = await conn.fetchval(sql, *params)
    return Response(content=bytes(tile or b""), media_type="application/vnd.mapbox-vector-tile",
                    headers={"Cache-Control": "public, max-age=3600"})
