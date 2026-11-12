"""Teselas vectoriales Mapbox Vector Tile (ST_AsMVT) para renderizado masivo en MapLibre.

* zoom >= 13: un punto por siniestro con sus atributos.
* zoom < 13: agregación por celda de pantalla (4-8 px), hora, severidad y obra. Al
  conservar ``hour``, ``severity`` y ``workzone`` como atributos, el cliente puede
  seguir filtrando en GPU (``map.setFilter``) sin pedir nuevas teselas; ``count``
  sirve de peso del heatmap.

Rendimiento: se usa la columna generada ``geom_3857`` (migración 0005) con su índice
GiST, así que ningún punto se reproyecta por petición. Las teselas agregadas, las
más caras porque a z9-z12 cubren gran parte de la ciudad, se guardan en una caché
por proceso de 10 minutos.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException, Path, Query, Response

from app.core.database import connection
from app.core.http_cache import TTLCache

router = APIRouter()

EXTENT = 4096
DETAIL_ZOOM = 13
MIN_ZOOM = 0
MAX_ZOOM = 22

POINTS_SQL = """
WITH env AS (SELECT ST_TileEnvelope($1, $2, $3) AS e3857),
mvt AS (
    SELECT ST_AsMVTGeom(c.geom_3857, env.e3857, {extent}, 64, true) AS geom,
           c.crash_record_id AS id, c.severity, c.crash_hour AS hour, c.crash_day_of_week AS dow,
           c.injuries_total AS injuries, c.injuries_fatal AS fatal, c.active_workzone AS workzone,
           1 AS count
    FROM silver_crashes c, env
    WHERE c.geom_3857 && env.e3857 {filters}
)
SELECT ST_AsMVT(mvt, 'crashes', {extent}, 'geom') FROM mvt WHERE geom IS NOT NULL
"""

AGG_SQL = """
WITH env AS (SELECT ST_TileEnvelope($1, $2, $3) AS e3857),
pts AS (
    SELECT ST_SnapToGrid(ST_AsMVTGeom(c.geom_3857, env.e3857, {extent}, 64, true), {snap}) AS g,
           c.severity, c.crash_hour, c.active_workzone, c.injuries_fatal
    FROM silver_crashes c, env
    WHERE c.geom_3857 && env.e3857 {filters}
),
mvt AS (
    SELECT g AS geom, severity, crash_hour AS hour, active_workzone AS workzone,
           count(*)::int AS count, sum(injuries_fatal)::int AS fatal
    FROM pts WHERE g IS NOT NULL
    GROUP BY g, severity, crash_hour, active_workzone
)
SELECT ST_AsMVT(mvt, 'crashes', {extent}, 'geom') FROM mvt
"""

_agg_cache = TTLCache(maxsize=256, ttl=600)


@router.get("/crashes/{z}/{x}/{y}.pbf", summary="Tesela vectorial MVT de siniestros",
            response_class=Response)
async def crash_tile(
    z: int = Path(..., ge=MIN_ZOOM, le=MAX_ZOOM),
    x: int = Path(..., ge=0),
    y: int = Path(..., ge=0),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    workzone_only: bool = Query(False, description="Sólo siniestros a <= 250 m de una obra CDOT activa"),
) -> Response:
    if x >= 2 ** z or y >= 2 ** z:
        raise HTTPException(status_code=404, detail="Tesela fuera de rango")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date debe ser <= end_date")
    params: list = [z, x, y]
    filters = ""
    if start_date:
        params.append(start_date)
        filters += f" AND c.crash_date >= ${len(params)}"
    if end_date:
        params.append(end_date)
        filters += f" AND c.crash_date < (${len(params)}::date + 1)"
    if workzone_only:
        filters += " AND c.active_workzone"

    detail = z >= DETAIL_ZOOM
    key = None if detail else (z, x, y, start_date, end_date, workzone_only)
    tile = _agg_cache.get(key) if key else None
    if tile is None:
        template = POINTS_SQL if detail else AGG_SQL
        snap = 32 if z <= 10 else 16  # celda de agregación en unidades de tesela
        sql = template.format(extent=EXTENT, filters=filters, snap=snap)
        async with connection() as conn:
            tile = bytes(await conn.fetchval(sql, *params) or b"")
        if key:
            _agg_cache.set(key, tile)
    return Response(content=tile, media_type="application/vnd.mapbox-vector-tile",
                    headers={"Cache-Control": "public, max-age=3600"})
