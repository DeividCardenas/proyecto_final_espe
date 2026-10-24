"""Ingeniería de características espaciotemporales (Fase 3).

``build_features`` es la única fuente de verdad de la transformación y se usa
tanto en el entrenamiento como en la inferencia en vivo de la API, garantizando
que ambos caminos producen exactamente las mismas columnas.

Uso:
    python -m app.ml.feature_engineering --output /data/processed/features_gold.parquet
"""
from __future__ import annotations

import argparse
import logging
import time

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.database import raw_connection
from app.core.severity import GRID_SIZE_FT

logger = logging.getLogger("ml.features")

NUMERIC_FEATURES = [
    "hour_sin", "hour_cos", "crash_hour", "day_of_week", "crash_month", "is_weekend", "is_rush_hour",
    "is_night", "posted_speed_limit", "aadt_log", "aadt_imputed", "active_workzone",
    "intersection_related", "grid_density", "latitude", "longitude",
    # Mecanismo del siniestro (en inferencia se marginalizan, ver MECHANISM_FEATURES)
    "num_units", "hit_and_run", "has_motorcycle", "has_pedestrian", "has_cyclist",
]
CATEGORICAL_FEATURES = [
    "weather_group", "lighting_group", "surface_group", "trafficway_type", "traffic_control_device",
    "first_crash_type", "prim_contributory_cause",
]
# Variables que describen CÓMO ocurre el siniestro. Para evaluar un tramo (sin
# siniestro concreto) la API promedia la predicción sobre los perfiles de
# mecanismo más frecuentes, ponderados por su frecuencia histórica.
MECHANISM_FEATURES = ["first_crash_type", "prim_contributory_cause", "num_units", "hit_and_run", "has_motorcycle", "has_pedestrian",
                      "has_cyclist"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "target"

WEATHER_GROUPS = {
    "CLEAR": "CLEAR",
    "CLOUDY/OVERCAST": "CLEAR",
    "RAIN": "RAIN",
    "FREEZING RAIN/DRIZZLE": "RAIN",
    "SLEET/HAIL": "SNOW",
    "SNOW": "SNOW",
    "BLOWING SNOW": "SNOW",
    "FOG/SMOKE/HAZE": "FOG",
    "SEVERE CROSS WIND GATE": "OTHER",
    "BLOWING SAND, SOIL, DIRT": "OTHER",
    "OTHER": "OTHER",
}
LIGHTING_GROUPS = {
    "DAYLIGHT": "DAY",
    "DARKNESS, LIGHTED ROAD": "DARK_LIGHTED",
    "DARKNESS": "DARK",
    "DUSK": "DUSK_DAWN",
    "DAWN": "DUSK_DAWN",
}
SURFACE_GROUPS = {
    "DRY": "DRY",
    "WET": "WET",
    "SNOW OR SLUSH": "SNOW_ICE",
    "ICE": "SNOW_ICE",
    "SAND, MUD, DIRT": "OTHER",
    "OTHER": "OTHER",
}
# Alias aceptados por la API (p. ej. "DARKNESS" o "RAIN" directamente)
WEATHER_ALIASES = {"CLEAR": "CLEAR", "RAIN": "RAIN", "SNOW": "SNOW", "FOG": "FOG", "OTHER": "OTHER"}
LIGHTING_ALIASES = {"DAY": "DAY", "DARK_LIGHTED": "DARK_LIGHTED", "DARK": "DARK", "DUSK_DAWN": "DUSK_DAWN"}

EXTRACT_SQL = f"""
WITH base AS (
    SELECT crash_record_id, crash_date, posted_speed_limit, weather_condition, lighting_condition,
           roadway_surface_cond, trafficway_type, traffic_control_device, intersection_related_i,
           aadt_volume, aadt_imputed, active_workzone, latitude, longitude,
           first_crash_type, prim_contributory_cause, num_units, hit_and_run_i,
           floor(ST_X(geom_3435) / {GRID_SIZE_FT})::int AS grid_x,
           floor(ST_Y(geom_3435) / {GRID_SIZE_FT})::int AS grid_y,
           severity AS target
    FROM silver_crashes
    WHERE geom IS NOT NULL AND crash_date IS NOT NULL
), units AS (
    SELECT crash_record_id,
           bool_or(vehicle_type ILIKE '%%MOTORCYCLE%%' OR vehicle_type ILIKE 'MOPED%%'
                   OR vehicle_type = 'AUTOCYCLE') AS has_motorcycle,
           bool_or(unit_type = 'PEDESTRIAN') AS has_pedestrian,
           bool_or(unit_type IN ('BICYCLE', 'NON-MOTOR VEHICLE')) AS has_cyclist
    FROM silver_vehicles GROUP BY crash_record_id
), span AS (
    SELECT greatest(extract(epoch FROM max(crash_date) - min(crash_date)) / (365.25 * 86400), 1.0) AS years
    FROM base
)
SELECT b.*, u.has_motorcycle, u.has_pedestrian, u.has_cyclist,
       -- Densidad histórica de siniestros por año en la celda de 500 m
       (count(*) OVER (PARTITION BY grid_x, grid_y)) / span.years AS grid_density
FROM base b CROSS JOIN span LEFT JOIN units u USING (crash_record_id)
"""


def _group(series: pd.Series, mapping: dict, aliases: dict | None = None) -> pd.Series:
    s = series.astype("string").str.upper().str.strip()
    mapped = s.map(mapping)
    if aliases:
        mapped = mapped.fillna(s.map(aliases))
    return mapped.fillna("UNKNOWN").astype(str)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma atributos crudos de siniestro / tramo en la matriz de modelado.

    Columnas de entrada aceptadas: ``crash_date`` (o ``crash_hour`` +
    ``day_of_week`` + ``crash_month``), ``weather_condition``,
    ``lighting_condition``, ``roadway_surface_cond``, ``posted_speed_limit``,
    ``trafficway_type``, ``traffic_control_device``, ``intersection_related_i``,
    ``aadt_volume``, ``aadt_imputed``, ``active_workzone``, ``grid_density``,
    ``latitude``, ``longitude``.
    """
    out = pd.DataFrame(index=df.index)

    def num(col: str) -> pd.Series:
        if col not in df.columns:
            return pd.Series(np.nan, index=df.index, dtype=float)
        return pd.to_numeric(df[col], errors="coerce").astype(float)

    if "crash_date" in df.columns and df["crash_date"].notna().any():
        ts = pd.to_datetime(df["crash_date"])
        hour, dow, month = ts.dt.hour, ts.dt.dayofweek, ts.dt.month
    else:
        hour, dow, month = df["crash_hour"], df["day_of_week"], df["crash_month"]
    hour = hour.astype(float)
    out["crash_hour"] = hour
    out["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    out["day_of_week"] = dow.astype(float)  # 0 = lunes ... 6 = domingo
    out["crash_month"] = month.astype(float)
    out["is_weekend"] = (dow >= 5).astype(float)
    out["is_rush_hour"] = (((hour >= 7) & (hour <= 9)) | ((hour >= 16) & (hour <= 18))).astype(float) * (dow < 5)
    out["is_night"] = ((hour >= 21) | (hour <= 5)).astype(float)

    out["posted_speed_limit"] = num("posted_speed_limit")
    aadt = num("aadt_volume")
    out["aadt_log"] = np.log1p(aadt)
    out["aadt_imputed"] = df.get("aadt_imputed", pd.Series(False, index=df.index)).fillna(True).astype(float)
    out["active_workzone"] = df.get("active_workzone", pd.Series(False, index=df.index)).fillna(False).astype(float)
    inter = df.get("intersection_related_i", pd.Series(pd.NA, index=df.index))
    out["intersection_related"] = pd.Series(inter, index=df.index).map({True: 1.0, False: 0.0}).astype(float)
    out["grid_density"] = num("grid_density")
    out["latitude"] = num("latitude")
    out["longitude"] = num("longitude")

    def flag(col: str) -> pd.Series:
        v = df.get(col, pd.Series(pd.NA, index=df.index))
        return pd.Series(v, index=df.index).map({True: 1.0, False: 0.0, 1: 1.0, 0: 0.0}).fillna(0.0).astype(float)

    out["num_units"] = num("num_units").clip(upper=6)
    out["hit_and_run"] = flag("hit_and_run_i")
    out["has_motorcycle"] = flag("has_motorcycle")
    out["has_pedestrian"] = flag("has_pedestrian")
    out["has_cyclist"] = flag("has_cyclist")

    na = pd.Series(pd.NA, index=df.index)
    out["weather_group"] = _group(df.get("weather_condition", na), WEATHER_GROUPS, WEATHER_ALIASES)
    out["lighting_group"] = _group(df.get("lighting_condition", na), LIGHTING_GROUPS, LIGHTING_ALIASES)
    out["surface_group"] = _group(df.get("roadway_surface_cond", na), SURFACE_GROUPS,
                                  {v: v for v in set(SURFACE_GROUPS.values())})
    for col in ("trafficway_type", "traffic_control_device", "first_crash_type", "prim_contributory_cause"):
        out[col] = df.get(col, na).astype("string").str.upper().fillna("UNKNOWN").astype(str)
    return out[FEATURES]


def extract(output: str) -> pd.DataFrame:
    t0 = time.perf_counter()
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute(EXTRACT_SQL)
        cols = [d.name for d in cur.description]
        raw = pd.DataFrame(cur.fetchall(), columns=cols)
    feats = build_features(raw)
    feats[TARGET] = raw["target"].astype(int)
    feats["crash_record_id"] = raw["crash_record_id"]
    feats["crash_date"] = pd.to_datetime(raw["crash_date"])
    feats["grid_x"] = raw["grid_x"]
    feats["grid_y"] = raw["grid_y"]
    feats.to_parquet(output, compression="snappy", index=False)
    logger.info("Matriz de características: %d filas x %d columnas en %.1fs -> %s",
                len(feats), len(FEATURES), time.perf_counter() - t0, output)
    logger.info("Distribución del target: %s", feats[TARGET].value_counts(normalize=True).round(4).to_dict())
    return feats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Extracción de la matriz analítica de características")
    parser.add_argument("--output", default=str(settings.processed_dir / "features_gold.parquet"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    extract(args.output)


if __name__ == "__main__":
    main()
