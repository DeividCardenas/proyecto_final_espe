"""Capa Gold analítica en DuckDB (OLAP embebido) alimentada desde PostGIS.

* ``export_gold()``: materializa hechos de siniestros y agregados Gold en
  ``chicago_olap.duckdb`` y en Parquet (``data/processed/gold_*.parquet``).
* ``query()``: consultas de sólo lectura para la API sobre una conexión reutilizable
  que se reabre cuando el archivo cambia.
* Toda escritura (``export_gold``, ``attach_table``) se hace sobre una copia que
  reemplaza al archivo de forma atómica, así nunca choca con el bloqueo de la API.

Uso:
    python -m app.services.olap.duckdb_engine --export
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import threading
import time
from pathlib import Path

import duckdb
import pandas as pd

from app.core.config import settings
from app.core.database import raw_connection
from app.core.errors import OlapUnavailableError
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
        # Conserva las salidas de los modelos del último entrenamiento (Fase 3)
        for table in ("gold_grid_ml", "gold_segment_risk"):
            src = settings.processed_dir / f"{table}.parquet"
            if src.exists():
                con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_parquet('{src.as_posix()}')")
                stats[table] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    # Reemplazo atómico: los lectores nunca ven un archivo a medio escribir
    os.replace(tmp, path)
    _reader.invalidate()
    stats["elapsed_s"] = round(time.perf_counter() - t0, 1)
    logger.info("Capa Gold exportada a %s: %s", path, stats)
    return stats


def _rewrite_atomically(path: str, mutate) -> None:
    """Aplica ``mutate(con)`` sobre una copia del archivo y la publica con ``os.replace``.

    La API mantiene el archivo abierto en sólo lectura; escribirlo en sitio choca con
    su bloqueo (``IOException: Could not set lock``) y, a la inversa, deja a los
    lectores sin servicio mientras dura la escritura. Con copia + reemplazo atómico
    los lectores siguen viendo la versión anterior hasta que la nueva está completa.
    """
    path = path or settings.DUCKDB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    for leftover in (tmp, f"{tmp}.wal"):
        if os.path.exists(leftover):
            os.remove(leftover)
    if os.path.exists(path):
        shutil.copy2(path, tmp)
    try:
        with duckdb.connect(tmp) as con:
            mutate(con)
            con.execute("CHECKPOINT")
        os.replace(tmp, path)
    finally:
        for leftover in (tmp, f"{tmp}.wal"):
            if os.path.exists(leftover):
                os.remove(leftover)
    _reader.invalidate()


def attach_ml_grid(grid: pd.DataFrame, path: str | None = None) -> None:
    """Agrega/reemplaza la tabla de riesgo ML por celda (generada en Fase 3)."""
    attach_table("gold_grid_ml", grid, path)


def attach_table(name: str, df: pd.DataFrame, path: str | None = None) -> None:
    """Crea o reemplaza una tabla Gold a partir de un DataFrame (reemplazo atómico del archivo)."""
    if not name.isidentifier():
        raise ValueError(f"Nombre de tabla inválido: {name!r}")

    def mutate(con: duckdb.DuckDBPyConnection) -> None:
        con.register("tmp_df", df)
        con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM tmp_df")
        con.unregister("tmp_df")

    _rewrite_atomically(path or settings.DUCKDB_PATH, mutate)


# ------------------------------------------------------------------------------
# Lectura para la API
# ------------------------------------------------------------------------------
# Límites por proceso Uvicorn: con varios workers en un contenedor de 2 GB, el
# valor por defecto de DuckDB (80 % de la RAM del host) podría agotar la memoria.
READ_MEMORY_LIMIT = os.getenv("DUCKDB_MEMORY_LIMIT", "512MB")
READ_THREADS = int(os.getenv("DUCKDB_THREADS", "2"))
LOCK_RETRIES = 3


class _ReadOnlyDuckDB:
    """Conexión de sólo lectura reutilizable, reabierta cuando el archivo cambia.

    Abrir DuckDB en cada consulta cuesta milisegundos (lectura del catálogo) y
    multiplica los bloqueos de archivo. Se conserva una conexión por proceso y cada
    consulta usa su propio ``cursor()`` (seguro entre hilos). Si el ETL publica un
    archivo nuevo (``os.replace`` cambia inode/mtime), se reabre en la siguiente consulta.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._con: duckdb.DuckDBPyConnection | None = None
        self._key: tuple | None = None

    @staticmethod
    def _stat_key(path: str) -> tuple:
        st = os.stat(path)
        return (path, st.st_ino, st.st_mtime_ns, st.st_size)

    def invalidate(self) -> None:
        # No se llama a close(): cerrar la conexión padre invalida los cursores que
        # otros hilos estén usando. Al soltar la referencia, el recolector la cierra
        # cuando terminan las consultas en curso.
        with self._lock:
            self._con, self._key = None, None

    def cursor(self) -> duckdb.DuckDBPyConnection:
        path = settings.DUCKDB_PATH
        try:
            key = self._stat_key(path)
        except FileNotFoundError:
            self.invalidate()
            raise OlapUnavailableError("Capa Gold (DuckDB) no disponible: ejecute el pipeline ETL", None)
        with self._lock:
            if self._con is None or self._key != key:
                self._con = None
                self._con = self._open(path)
                self._key = key
            return self._con.cursor()

    @staticmethod
    def _open(path: str) -> duckdb.DuckDBPyConnection:
        last: Exception | None = None
        for attempt in range(LOCK_RETRIES):
            try:
                return duckdb.connect(path, read_only=True,
                                      config={"memory_limit": READ_MEMORY_LIMIT, "threads": READ_THREADS})
            except duckdb.IOException as exc:  # archivo bloqueado por un escritor antiguo
                last = exc
                time.sleep(0.2 * (attempt + 1))
        raise OlapUnavailableError("Capa Gold (DuckDB) ocupada; reintente en unos segundos") from last


_reader = _ReadOnlyDuckDB()


def query(sql: str, params: list | None = None) -> list[dict]:
    cur = _reader.cursor()
    try:
        cur.execute(sql, params or [])
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        cur.close()


def table_exists(name: str) -> bool:
    rows = query("SELECT count(*) AS n FROM information_schema.tables WHERE table_name = ?", [name])
    return bool(rows[0]["n"])


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Exportación de la Capa Gold a DuckDB")
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.export:
        print(export_gold())


if __name__ == "__main__":
    main()
