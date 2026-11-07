"""Punto de entrada FastAPI: lifespan tolerante a fallos, middlewares y routers."""
from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app import __version__
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import close_db_pool, init_db_pool
from app.core.errors import register_exception_handlers
from app.ml.predictor import RiskPredictor

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")
access_logger = logging.getLogger("app.access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Pool asyncpg. Si PostGIS aún no responde, la API arranca igual: /health
    #    informa DEGRADED (503) y el pool se crea en la primera petición que lo necesite.
    try:
        await init_db_pool()
        logger.info("Pool asyncpg listo")
    except Exception as exc:
        logger.warning("PostGIS no disponible al arrancar (%s); se reintentará bajo demanda", exc)

    # 2. Carga tolerante a fallos del modelo predictivo
    predictor = RiskPredictor(settings.MODEL_PATH)
    app.state.model_loaded = predictor.load()
    app.state.predictor = predictor

    yield

    # 3. Cierre ordenado
    await close_db_pool()


DESCRIPTION = """
API geoespacial de riesgo vial para la Ciudad de Chicago.

* **crashes**: siniestros en GeoJSON por ventana espacial, clusters DBSCAN y exportación NDJSON.
* **permits**: obras CDOT activas con su zona de influencia de 250 m.
* **analytics**: KPIs y agregaciones servidas desde la capa Gold en DuckDB.
* **risk**: rejilla de riesgo predicho por el modelo (celdas de 500 m) y riesgo por tramo vial.
* **predict**: inferencia de riesgo en vivo para un tramo vial.
* **tiles**: teselas vectoriales MVT de siniestros.

Los errores devuelven siempre JSON `{"detail": ...}`: 422 (parámetros inválidos),
404 (recurso inexistente), 429 (demasiadas operaciones pesadas a la vez),
503 (base de datos o capa Gold no disponibles) y 504 (consulta demasiado lenta).
"""

# Swagger/ReDoc activos por defecto (útiles para la defensa y la demo); API_DOCS=false los apaga.
_docs = os.getenv("API_DOCS", "true").lower() not in ("0", "false", "no")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=__version__,
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs" if _docs else None,
    redoc_url="/redoc" if _docs else None,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if _docs else None,
)
register_exception_handlers(app)


@app.middleware("http")
async def access_log(request: Request, call_next):
    """Registra método, ruta, estado y duración, y propaga un identificador de petición."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["Server-Timing"] = f"app;dur={ms:.1f}"
    if request.url.path != f"{settings.API_V1_STR}/health":
        access_logger.info("%s %s %s %d %.1fms", request_id, request.method, request.url.path,
                           response.status_code, ms)
    return response


# Nivel 5: medido con un GeoJSON de 50 000 siniestros (22 MB), comprime 5 veces más
# rápido que el 9 por defecto (140 ms frente a 700 ms) con un 10 % más de bytes.
# La compresión corre en el event loop, así que un nivel alto bloquea a las demás peticiones.
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Server-Timing", "Retry-After"],
)
app.include_router(api_router, prefix=settings.API_V1_STR)
