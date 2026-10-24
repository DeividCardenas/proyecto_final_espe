"""Obras viales CDOT vigentes y su zona de influencia métrica."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query, Response

from app.core.database import get_pool
from app.schemas.spatial import METRO_BOUNDS

router = APIRouter()


@router.get("/active", summary="Obras CDOT activas en una fecha con buffer de 250 m (GeoJSON)")
async def active_permits(
    on_date: date | None = Query(None, alias="date", description="Fecha de vigencia (por defecto: la más reciente con datos)"),
    min_lon: float = Query(METRO_BOUNDS["min_lon"]),
    min_lat: float = Query(METRO_BOUNDS["min_lat"]),
    max_lon: float = Query(METRO_BOUNDS["max_lon"]),
    max_lat: float = Query(METRO_BOUNDS["max_lat"]),
    buffer_meters: float = Query(250, ge=10, le=1000),
    with_buffer: bool = Query(True, description="Incluir polígono de amortiguamiento"),
    limit: int = Query(3_000, ge=1, le=20_000),
) -> Response:
    buffer_ft = buffer_meters * 3.2808333
    async with get_pool().acquire() as conn:
        if on_date is None:
            on_date = await conn.fetchval(
                "SELECT least(current_date, max(application_end_date)::date) FROM silver_road_permits")
        body = await conn.fetchval(
            """
            WITH sel AS (
                SELECT * FROM silver_road_permits p
                WHERE p.geom && ST_MakeEnvelope($1, $2, $3, $4, 4326)
                  AND p.street_closure IN ('Full', 'Partial')
                  AND $5::date BETWEEN p.application_start_date::date AND p.application_end_date::date
                ORDER BY p.application_start_date DESC
                LIMIT $8
            )
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'date', $5::date,
                'features', coalesce(json_agg(json_build_object(
                    'type', 'Feature',
                    'id', p.permit_number,
                    'geometry', CASE WHEN $7
                        THEN ST_AsGeoJSON(ST_Transform(ST_Buffer(p.geom_3435, $6, 4), 4326), 6)::json
                        ELSE ST_AsGeoJSON(p.geom, 6)::json END,
                    'properties', json_build_object(
                        'permit', p.permit_number,
                        'work_type', p.work_type,
                        'description', p.work_type_description,
                        'closure', p.street_closure,
                        'street', concat_ws(' ', p.street_number, p.street_direction, p.street_name),
                        'start', p.application_start_date::date,
                        'end', p.application_end_date::date,
                        'lon', ST_X(p.geom), 'lat', ST_Y(p.geom)
                    )
                )), '[]'::json)
            )::text
            FROM sel p
            """,
            min_lon, min_lat, max_lon, max_lat, on_date, buffer_ft, with_buffer, limit,
        )
    return Response(content=body, media_type="application/geo+json",
                    headers={"Cache-Control": "public, max-age=600"})
