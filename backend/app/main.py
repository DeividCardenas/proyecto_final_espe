"""Punto de entrada FastAPI: lifespan resiliente, middlewares y routers."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import close_db_pool, init_db_pool
from app.ml.predictor import RiskPredictor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Pool de conexiones asíncronas (asyncpg)
    pool = await init_db_pool()
    async with pool.acquire() as conn:
        app.state.data_years = await conn.fetchval(
            "SELECT greatest(extract(epoch FROM max(crash_date) - min(crash_date)) / (365.25*86400), 1.0) "
            "FROM silver_crashes"
        ) or 1.0

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
* **risk**: rejilla de riesgo predicho por el modelo (celdas de 500 m).
* **predict**: inferencia de riesgo en vivo para un tramo vial.
"""

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.API_V1_STR)
