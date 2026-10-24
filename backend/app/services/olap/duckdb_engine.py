"""Capa Gold analítica en DuckDB (OLAP embebido) alimentada desde PostGIS.

* ``export_gold()``: materializa hechos de siniestros y agregados Gold en
  ``chicago_olap.duckdb`` y en Parquet (``data/processed/gold_*.parquet``).
* ``query()``: consultas de sólo lectura para la API (conexión efímera, para no
  bloquear al proceso ETL que escribe el archivo).

Uso:
    python -m app.services.olap.duckdb_engine --export
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

import duckdb
import pandas as pd

from app.core.config import settings
from app.core.database import raw_connection
from app.core.severity import GRID_SIZE_FT

logger = logging.getLogger("olap.duckdb")

FACTS_SQL = f"""
SELECT crash_record_id,
       crash_date,
       extract(year FROM crash_date)::int AS crash_year,
       crash_hour, crash_day_of_week, crash_month,
       latitude, longitude,
       posted_speed_limit, weather_condition, lighting_condition, roadway_surface_cond,
       trafficway_type, traffic_control_device, first_crash_type, prim_contributory_cause,
       beat_of_occurrence, street_name, damage, most_severe_injury,
       coalesce(injuries_total, 0) AS injuries_total,
       coalesce(injuries_fatal, 0) AS injuries_fatal,
       coalesce(injuries_incapacitating, 0) AS injuries_incapacitating,
       aadt_volume, aadt_imputed, active_workzone,
       floor(ST_X(geom_3435) / {GRID_SIZE_FT})::int AS grid_x,
       floor(ST_Y(geom_3435) / {GRID_SIZE_FT})::int AS grid_y,
       severity
FROM silver_crashes
WHERE geom IS NOT NULL
"""

GOLD_TABLES = {
    "gold_hourly": """
        SELECT crash_hour, crash_day_of_week, count(*) AS crashes,
               sum(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS critical,
               sum(injuries_total) AS injuries, sum(injuries_fatal) AS fatalities
        FROM gold_crash_facts GROUP BY ALL ORDER BY ALL
    """,
    "gold_monthly": """
        SELECT date_trunc('month', crash_date) AS month, count(*) AS crashes,
               sum(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS critical,
               sum(injuries_fatal) AS fatalities
        FROM gold_crash_facts GROUP BY ALL ORDER BY ALL
    """,
    "gold_weather": """
        SELECT coalesce(weather_condition, 'UNKNOWN') AS weather_condition, count(*) AS crashes,
               avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END) AS critical_rate
        FROM gold_crash_facts GROUP BY ALL ORDER BY crashes DESC
    """,
    "gold_causes": """
        SELECT coalesce(prim_contributory_cause, 'UNKNOWN') AS cause, count(*) AS crashes,
               avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END) AS critical_rate
        FROM gold_crash_facts GROUP BY ALL ORDER BY crashes DESC
    """,
    "gold_grid": """
        SELECT grid_x, grid_y, count(*) AS crashes,
               sum(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS critical,
               avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END) AS critical_rate,
               sum(injuries_fatal) AS fatalities,
               avg(longitude) AS lon, avg(latitude) AS lat,
               avg(aadt_volume) AS mean_aadt,
               avg(CASE WHEN active_workzone THEN 1.0 ELSE 0.0 END) AS workzone_rate
        FROM gold_crash_facts GROUP BY grid_x, grid_y
    """,
    "gold_aadt_severity": """
        SELECT ntile(20) OVER (ORDER BY aadt_volume) AS aadt_bucket, aadt_volume, severity
        FROM gold_crash_facts WHERE NOT aadt_imputed
    """,
}


def fetch_facts() -> pd.DataFrame:
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute(FACTS_SQL)
        cols = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def export_gold(path: str | None = None) -> dict:
    path = path or settings.DUCKDB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    facts = fetch_facts()
    tmp = f"{path}.tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    stats = {"facts": len(facts)}
    with duckdb.connect(tmp) as con:
        con.register("facts_df", facts)
        con.execute("CREATE TABLE gold_crash_facts AS SELECT * FROM facts_df")
        for name, sql in GOLD_TABLES.items():
            con.execute(f"CREATE TABLE {name} AS {sql}")
            stats[name] = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        settings.processed_dir.mkdir(parents=True, exist_ok=True)
        out = (settings.processed_dir / "gold_crash_facts.parquet").as_posix()
        con.execute(f"COPY gold_crash_facts TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    # Reemplazo atómico: los lectores nunca ven un archivo a medio escribir
    os.replace(tmp, path)
    stats["elapsed_s"] = round(time.perf_counter() - t0, 1)
    logger.info("Capa Gold exportada a %s: %s", path, stats)
    return stats


def attach_ml_grid(grid: pd.DataFrame, path: str | None = None) -> None:
    """Agrega/reemplaza la tabla de riesgo ML por celda (generada en Fase 3)."""
    path = path or settings.DUCKDB_PATH
    with duckdb.connect(path) as con:
        con.register("grid_df", grid)
        con.execute("CREATE OR REPLACE TABLE gold_grid_ml AS SELECT * FROM grid_df")


def query(sql: str, params: list | None = None) -> list[dict]:
    if not os.path.exists(settings.DUCKDB_PATH):
        raise FileNotFoundError(settings.DUCKDB_PATH)
    with duckdb.connect(settings.DUCKDB_PATH, read_only=True) as con:
        cur = con.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Exportación de la Capa Gold a DuckDB")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.export:
        print(export_gold())


if __name__ == "__main__":
    main()
