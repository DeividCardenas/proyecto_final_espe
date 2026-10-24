import os

from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.database import get_pool

router = APIRouter()


@router.get("/health", summary="Sonda de salud y diagnóstico")
async def health(request: Request) -> dict:
    db_ok, postgis = False, None
    try:
        async with get_pool().acquire() as conn:
            postgis = await conn.fetchval("SELECT postgis_lib_version()")
            db_ok = True
    except Exception:  # la sonda nunca debe lanzar excepción
        pass
    predictor = getattr(request.app.state, "predictor", None)
    return {
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
