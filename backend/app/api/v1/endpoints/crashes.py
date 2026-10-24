"""Endpoints geoespaciales de siniestros (GeoJSON nativo en SQL, DBSCAN, NDJSON)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from app.core.database import get_pool
from app.schemas.spatial import CrashFilters, crash_filters

router = APIRouter()

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
            SELECT * FROM silver_crashes c
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
    async with get_pool().acquire() as conn:
        body = await conn.fetchval(sql, *params)
    return Response(content=body, media_type="application/geo+json",
                    headers={"Cache-Control": "public, max-age=300"})


@router.get("/clusters", summary="Puntos calientes de siniestralidad (ST_ClusterDBSCAN)")
async def crash_clusters(
    f: CrashFilters = Depends(crash_filters),
    eps_meters: float = Query(40, ge=5, le=500, description="Radio de vecindad DBSCAN en metros"),
    min_points: int = Query(15, ge=2, le=500, description="Siniestros mínimos para formar un núcleo"),
    sample: int = Query(100_000, ge=1_000, le=500_000, description="Máximo de siniestros evaluados"),
    limit: int = Query(500, ge=1, le=5_000),
) -> dict:
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
    async with get_pool().acquire() as conn:
        rows = await conn.fetch(sql, *params)
    return {
        "type": "FeatureCollection",
        "eps_meters": eps_meters,
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
             "properties": {"cluster_id": r["cid"], "count": r["n"], "critical": r["critical"],
                            "fatalities": r["fatalities"]}}
            for r in rows
        ],
    }


@router.get("/stream", summary="Exportación masiva NDJSON en streaming")
async def crashes_stream(
    f: CrashFilters = Depends(crash_filters),
    limit: int = Query(100_000, ge=1, le=1_000_000),
) -> StreamingResponse:
    where, params = f.where("c")
    params.append(limit)
    sql = f"""
        SELECT json_build_object('lon', ST_X(c.geom), 'lat', ST_Y(c.geom), {FEATURE_PROPS})::text AS j
        FROM silver_crashes c WHERE {where}
        ORDER BY c.crash_date DESC LIMIT ${len(params)}
    """

    async def gen():
        async with get_pool().acquire() as conn:
            async with conn.transaction():
                async for rec in conn.cursor(sql, *params, prefetch=2000):
                    yield rec["j"] + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson",
                             headers={"Content-Disposition": "attachment; filename=chicago_crashes.ndjson"})


@router.get("/{crash_record_id}", summary="Detalle de un siniestro con vehículos y personas (anonimizadas)")
async def crash_detail(crash_record_id: str) -> dict:
    async with get_pool().acquire() as conn:
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
