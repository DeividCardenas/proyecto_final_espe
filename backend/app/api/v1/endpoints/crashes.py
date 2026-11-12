"""Endpoints geoespaciales de siniestros (GeoJSON nativo en SQL, DBSCAN, NDJSON)."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.core.database import connection, ensure_pool
from app.core.errors import TooManyRequestsError
from app.core.http_cache import TTLCache, cached_bytes_response, dumps
from app.schemas.spatial import CrashFilters, crash_filters

router = APIRouter()

# Operaciones pesadas por proceso Uvicorn. Cada una retiene una conexión del pool
# (DB_POOL_MAX por worker), así que se acotan para que nunca dejen sin conexiones
# al resto de endpoints: si el cupo está lleno se responde 429 con Retry-After.
MAX_CONCURRENT_EXPORTS = 2
MAX_CONCURRENT_CLUSTERS = 2
_export_slots = asyncio.Semaphore(MAX_CONCURRENT_EXPORTS)
_cluster_slots = asyncio.Semaphore(MAX_CONCURRENT_CLUSTERS)
_cluster_cache = TTLCache(maxsize=64, ttl=600)

GEOJSON_COLUMNS = (
    "crash_record_id, crash_date, crash_hour, crash_day_of_week, severity, injuries_total, injuries_fatal, "
    "weather_condition, lighting_condition, posted_speed_limit, prim_contributory_cause, street_no, "
    "street_direction, street_name, first_crash_type, active_workzone, aadt_volume, geom"
)


async def _take_slot(sem: asyncio.Semaphore, what: str) -> None:
    try:
        await asyncio.wait_for(sem.acquire(), timeout=2)
    except asyncio.TimeoutError:
        raise TooManyRequestsError(f"Hay demasiadas {what} en curso; reintente en unos segundos") from None

FEATURE_PROPS = """
    'id', c.crash_record_id,
    'date', to_char(c.crash_date, 'YYYY-MM-DD"T"HH24:MI'),
    'hour', c.crash_hour,
    'dow', c.crash_day_of_week,
    'severity', c.severity,
    'injuries', c.injuries_total,
    'fatal', c.injuries_fatal,
    'weather', c.weather_condition,
    'lighting', c.lighting_condition,
    'speed', c.posted_speed_limit,
    'cause', c.prim_contributory_cause,
    'street', concat_ws(' ', c.street_no, c.street_direction, c.street_name),
    'crash_type', c.first_crash_type,
    'workzone', c.active_workzone,
    'aadt', c.aadt_volume
"""


@router.get("/geojson", summary="Siniestros en una ventana espacial (GeoJSON FeatureCollection)")
async def crashes_geojson(
    f: CrashFilters = Depends(crash_filters),
    limit: int = Query(10_000, ge=1, le=50_000, description="Máximo de entidades (las más recientes)"),
) -> Response:
    where, params = f.where("c")
    params.append(limit)
    # La CTE limita las filas ANTES de json_agg (evita materializar todo el BBOX en memoria)
    sql = f"""
        WITH sel AS (
            SELECT {GEOJSON_COLUMNS} FROM silver_crashes c
            WHERE {where}
            ORDER BY c.crash_date DESC
            LIMIT ${len(params)}
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', coalesce(json_agg(json_build_object(
                'type', 'Feature',
                'id', c.crash_record_id,
                'geometry', ST_AsGeoJSON(c.geom, 6)::json,
                'properties', json_build_object({FEATURE_PROPS})
            )), '[]'::json)
        )::text
        FROM sel c
    """
    async with connection() as conn:
        body = await conn.fetchval(sql, *params)
    return Response(content=body, media_type="application/geo+json",
                    headers={"Cache-Control": "public, max-age=300"})


@router.get("/clusters", summary="Puntos calientes de siniestralidad (ST_ClusterDBSCAN)")
async def crash_clusters(
    request: Request,
    f: CrashFilters = Depends(crash_filters),
    eps_meters: float = Query(40, ge=5, le=500, description="Radio de vecindad DBSCAN en metros"),
    min_points: int = Query(15, ge=2, le=500, description="Siniestros mínimos para formar un núcleo"),
    sample: int = Query(100_000, ge=1_000, le=200_000, description="Máximo de siniestros evaluados"),
    limit: int = Query(500, ge=1, le=5_000),
) -> Response:
    """Detecta concentraciones (típicamente intersecciones) con DBSCAN en EPSG:3435.

    Nota: con radios grandes la alta densidad urbana de Chicago encadena toda la
    ciudad en un único cluster; por eso el radio por defecto es de 40 m y la
    agrupación visual por nivel de zoom se delega al cliente (Supercluster).
    """
    eps_ft = eps_meters * 3.2808333
    where, params = f.where("c")
    params += [sample, eps_ft, min_points, limit]
    n = len(params)
    sql = f"""
        WITH pts AS (
            SELECT c.geom, c.geom_3435, c.severity, c.injuries_fatal FROM silver_crashes c
            WHERE {where}
            ORDER BY c.crash_date DESC LIMIT ${n-3}
        ), cl AS (
            SELECT geom, severity, injuries_fatal,
                   ST_ClusterDBSCAN(geom_3435, eps := ${n-2}, minpoints := ${n-1}) OVER () AS cid
            FROM pts
        )
        SELECT cid, count(*) AS n,
               sum((severity = 2)::int) AS critical,
               sum(injuries_fatal) AS fatalities,
               ST_X(ST_Centroid(ST_Collect(geom))) AS lon, ST_Y(ST_Centroid(ST_Collect(geom))) AS lat
        FROM cl WHERE cid IS NOT NULL
        GROUP BY cid ORDER BY n DESC LIMIT ${n}
    """
    # DBSCAN es CPU intensivo: los mismos parámetros se sirven desde caché 10 minutos
    key = (tuple(map(str, params)), eps_meters)
    body = _cluster_cache.get(key)
    if body is None:
        await _take_slot(_cluster_slots, "detecciones de puntos calientes")
        try:
            async with connection() as conn:
                rows = await conn.fetch(sql, *params)
        finally:
            _cluster_slots.release()
        body = dumps({
            "type": "FeatureCollection",
            "eps_meters": eps_meters,
            "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
                 "properties": {"cluster_id": r["cid"], "count": r["n"], "critical": r["critical"],
                                "fatalities": r["fatalities"]}}
                for r in rows
            ],
        })
        _cluster_cache.set(key, body)
    return cached_bytes_response(request, body, media_type="application/geo+json", max_age=600)


@router.get("/stream", summary="Exportación masiva NDJSON en streaming")
async def crashes_stream(
    f: CrashFilters = Depends(crash_filters),
    limit: int = Query(100_000, ge=1, le=300_000, description="Máximo de filas exportadas (las más recientes)"),
) -> StreamingResponse:
    where, params = f.where("c")
    params.append(limit)
    sql = f"""
        SELECT json_build_object('lon', ST_X(c.geom), 'lat', ST_Y(c.geom), {FEATURE_PROPS})::text AS j
        FROM silver_crashes c WHERE {where}
        ORDER BY c.crash_date DESC LIMIT ${len(params)}
    """

    # La exportación retiene una conexión mientras el cliente descarga: se limita el
    # número de exportaciones simultáneas y se valida la BD antes de empezar a emitir
    # (un error dentro del generador ya no puede convertirse en un código HTTP).
    await ensure_pool()
    await _take_slot(_export_slots, "exportaciones")

    async def gen():
        try:
            async with connection() as conn:
                async with conn.transaction(readonly=True):
                    batch: list[str] = []
                    async for rec in conn.cursor(sql, *params, prefetch=2000):
                        batch.append(rec["j"])
                        if len(batch) >= 2000:
                            yield "\n".join(batch) + "\n"
                            batch.clear()
                    if batch:
                        yield "\n".join(batch) + "\n"
        finally:
            _export_slots.release()

    return StreamingResponse(gen(), media_type="application/x-ndjson",
                             headers={"Content-Disposition": "attachment; filename=chicago_crashes.ndjson"})


@router.get("/{crash_record_id}", summary="Detalle de un siniestro con vehículos y personas (anonimizadas)")
async def crash_detail(crash_record_id: str = Path(..., min_length=1, max_length=128)) -> dict:
    async with connection() as conn:
        row = await conn.fetchrow(
            "SELECT json_build_object('lon', ST_X(c.geom), 'lat', ST_Y(c.geom), "
            f"{FEATURE_PROPS}, 'damage', c.damage, 'surface', c.roadway_surface_cond, "
            "'trafficway', c.trafficway_type, 'permit', c.workzone_permit_id, "
            "'aadt_distance_m', round(c.aadt_distance_m::numeric, 1))::text AS j "
            "FROM silver_crashes c WHERE c.crash_record_id = $1", crash_record_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Siniestro no encontrado")
        vehicles = await conn.fetch(
            "SELECT unit_type, vehicle_type, maneuver, vehicle_year FROM silver_vehicles "
            "WHERE crash_record_id = $1 ORDER BY unit_no", crash_record_id)
        people = await conn.fetch(
            "SELECT person_type, sex, age, injury_classification, safety_equipment FROM silver_people "
            "WHERE crash_record_id = $1", crash_record_id)
    detail = json.loads(row["j"])
    detail["vehicles"] = [dict(v) for v in vehicles]
    detail["people"] = [dict(p) for p in people]
    return detail
