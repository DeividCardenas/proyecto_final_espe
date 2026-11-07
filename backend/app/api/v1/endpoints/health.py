"""Sondas de salud.

* ``/live``: el proceso responde (no toca dependencias). Para reinicios por cuelgue.
* ``/health``: diagnóstico completo. Devuelve **503** cuando PostGIS no responde,
  para que Docker y nginx dejen de considerar sano un backend sin base de datos.
"""
import asyncio
import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import connection

router = APIRouter()

HEALTH_DB_TIMEOUT_S = 2.0


async def _db_probe() -> str:
    async with connection(timeout=HEALTH_DB_TIMEOUT_S) as conn:
        return await conn.fetchval("SELECT postgis_lib_version()", timeout=HEALTH_DB_TIMEOUT_S)


@router.get("/live", summary="Sonda de vida (sin dependencias)")
async def live() -> dict:
    return {"status": "UP"}


@router.get("/health", summary="Sonda de salud y diagnóstico (503 si la base de datos no responde)")
async def health(request: Request) -> JSONResponse:
    db_ok, postgis = False, None
    try:
        postgis = await asyncio.wait_for(_db_probe(), timeout=HEALTH_DB_TIMEOUT_S * 2)
        db_ok = True
    except Exception:  # la sonda nunca debe lanzar excepción
        pass
    predictor = getattr(request.app.state, "predictor", None)
    body = {
        "status": "UP" if db_ok else "DEGRADED",
        "database": {"connected": db_ok, "postgis_version": postgis},
        "model": {
            "loaded": bool(getattr(request.app.state, "model_loaded", False)),
            "algorithm": predictor.meta.get("algorithm") if predictor else None,
            "mode": "ml" if predictor and predictor.loaded else "heuristic_fallback",
        },
        "olap": {"duckdb_available": os.path.exists(settings.DUCKDB_PATH)},
        "environment": settings.ENVIRONMENT,
    }
    return JSONResponse(body, status_code=200 if db_ok else 503, headers={"Cache-Control": "no-store"})
