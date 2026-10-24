"""Estaciones de aforo vehicular (AADT) para la capa de círculos proporcionales."""
from fastapi import APIRouter, Response

from app.core.database import get_pool

router = APIRouter()


@router.get("/stations", summary="Estaciones de aforo AADT (GeoJSON)")
async def stations() -> Response:
    async with get_pool().acquire() as conn:
        body = await conn.fetchval("""
            SELECT json_build_object('type', 'FeatureCollection', 'features', coalesce(json_agg(json_build_object(
                'type', 'Feature', 'id', id,
                'geometry', ST_AsGeoJSON(geom, 6)::json,
                'properties', json_build_object(
                    'volume', total_passing_vehicle_volume,
                    'street', concat_ws(' ', traffic_volume_count_location_address, street),
                    'date', date_of_count::date,
                    'by_direction', vehicle_volume_by_each_direction_of_traffic)
            )), '[]'::json))::text
            FROM silver_traffic_counts WHERE geom IS NOT NULL
        """)
    return Response(content=body, media_type="application/geo+json",
                    headers={"Cache-Control": "public, max-age=86400"})
