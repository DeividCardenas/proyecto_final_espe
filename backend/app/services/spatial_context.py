"""Estadísticos globales de PostGIS que la inferencia necesita en cada petición.

Antes ``data_years`` se leía una sola vez al arrancar la API: si la API se levantaba
antes de cargar los datos (instalación nueva) quedaba en 1.0 hasta reiniciar, y
``grid_density`` salía unas 3 veces mayor que en el entrenamiento. Aquí se
recalculan con una caché corta, de modo que un ETL nuevo se refleja solo.

Definición (idéntica a ``feature_engineering.FEATURES_SQL`` y al artefacto del modelo):
``grid_density = siniestros con geometría y fecha en la celda de 500 m /
greatest(años entre la primera y la última fecha, 1.0)``.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import asyncpg

logger = logging.getLogger("app.context")

CONTEXT_TTL_S = 600.0

STATS_SQL = """
SELECT extract(epoch FROM max(crash_date) - min(crash_date)) / (365.25 * 86400) AS span_years,
       (SELECT round(avg(total_passing_vehicle_volume)) FROM silver_traffic_counts) AS aadt_mean
FROM silver_crashes
WHERE geom IS NOT NULL AND crash_date IS NOT NULL
"""


@dataclass(frozen=True)
class GlobalStats:
    data_years: float
    aadt_mean: float | None
    source: str  # "database" | "model_meta" | "default"


_cache: tuple[float, GlobalStats] | None = None


def _fallback(meta: dict | None) -> GlobalStats:
    years = (meta or {}).get("grid_density_years")
    if years:
        return GlobalStats(float(years), None, "model_meta")
    return GlobalStats(1.0, None, "default")


async def global_stats(conn: asyncpg.Connection, meta: dict | None = None) -> GlobalStats:
    """Años de historia y AADT medio, con caché de ``CONTEXT_TTL_S`` segundos.

    Si la tabla está vacía (API levantada antes del ETL) no se cachea el valor por
    defecto: se usa el del artefacto del modelo y se vuelve a consultar en la siguiente petición.
    """
    global _cache
    now = time.monotonic()
    if _cache is not None and _cache[0] > now:
        return _cache[1]
    row = await conn.fetchrow(STATS_SQL)
    if row is None or row["span_years"] is None:
        logger.warning("silver_crashes vacía: grid_density usa el respaldo del modelo")
        return _fallback(meta)
    aadt_mean = float(row["aadt_mean"]) if row["aadt_mean"] is not None else None
    stats = GlobalStats(max(float(row["span_years"]), 1.0), aadt_mean, "database")
    _cache = (now + CONTEXT_TTL_S, stats)
    return stats


def reset_cache() -> None:
    global _cache
    _cache = None
