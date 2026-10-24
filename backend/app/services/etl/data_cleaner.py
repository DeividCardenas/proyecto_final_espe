"""Calidad, saneamiento, deduplicación y carga Bronze -> Silver (PostGIS).

Lee los Parquet crudos de ``data/raw/<dataset>/``, aplica las reglas de calidad,
escribe la versión curada en ``data/processed/silver_<dataset>.parquet`` y la
carga en PostgreSQL mediante ``COPY`` a una tabla temporal + ``INSERT ... ON
CONFLICT`` (upsert idempotente). Los siniestros con coordenadas inválidas se
aíslan en ``crashes_quarantine``.

Uso:
    python -m app.services.etl.data_cleaner --verify-integrity
    python -m app.services.etl.data_cleaner --datasets crashes vehicles
"""
from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg

from app.core.config import CHICAGO_BBOX, settings
from app.core.database import raw_connection

logger = logging.getLogger("etl.cleaner")

LOAD_ORDER = ["aadt", "permits", "crashes", "vehicles", "people"]

VALID_SEX = {"M", "F", "X"}


# ------------------------------------------------------------------------------
# Utilidades de lectura y tipado
# ------------------------------------------------------------------------------
def read_bronze(dataset: str) -> pd.DataFrame:
    folder = settings.raw_dir / dataset
    parts = sorted(folder.glob("part-*.parquet"))
    if not parts:
        raise FileNotFoundError(f"No hay archivos Bronze para '{dataset}' en {folder}. Ejecute soda_client primero.")
    return pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)


def to_int(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").round().astype("Int64")


def to_float(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").astype("float64")


def to_ts(s: pd.Series) -> pd.Series:
    """Normaliza marcas de tiempo ISO-8601 (hora local de Chicago, sin zona)."""
    ts = pd.to_datetime(s, errors="coerce", utc=False, format="ISO8601")
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("America/Chicago").dt.tz_localize(None)
    return ts


def to_bool(s: pd.Series) -> pd.Series:
    mapped = s.str.upper().map({"Y": True, "N": False, "TRUE": True, "FALSE": False})
    return mapped.astype("boolean")


def clean_str(s: pd.Series) -> pd.Series:
    s = s.astype("string").str.strip()
    return s.mask(s == "", pd.NA)


def in_bbox(lat: pd.Series, lon: pd.Series) -> pd.Series:
    b = CHICAGO_BBOX
    return lat.between(b["min_lat"], b["max_lat"]) & lon.between(b["min_lon"], b["max_lon"])


# ------------------------------------------------------------------------------
# Reglas por dataset
# ------------------------------------------------------------------------------
def clean_crashes(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    n_raw = len(df)
    df = df.copy()
    for c in df.columns:
        df[c] = clean_str(df[c])
    df = df[df["crash_record_id"].notna()]
    df["crash_date"] = to_ts(df["crash_date"])
    df["date_police_notified"] = to_ts(df["date_police_notified"])
    df = df[df["crash_date"].notna()]

    # Deduplicación estricta por clave natural (se conserva la última notificación)
    df = df.sort_values("date_police_notified").drop_duplicates("crash_record_id", keep="last")
    n_dupes = n_raw - len(df)

    int_cols = ["posted_speed_limit", "lane_cnt", "num_units", "injuries_total", "injuries_fatal",
                "injuries_incapacitating", "injuries_non_incapacitating", "injuries_reported_not_evident",
                "injuries_no_indication", "injuries_unknown", "crash_hour", "crash_day_of_week", "crash_month"]
    for c in int_cols:
        df[c] = to_int(df[c])
    for c in ["injuries_total", "injuries_fatal", "injuries_incapacitating", "injuries_non_incapacitating",
              "injuries_reported_not_evident", "injuries_no_indication", "injuries_unknown"]:
        df[c] = df[c].fillna(0)
    df.loc[~df["posted_speed_limit"].between(0, 70), "posted_speed_limit"] = pd.NA
    for c in ["intersection_related_i", "hit_and_run_i", "work_zone_i"]:
        df[c] = to_bool(df[c])
    df["latitude"] = to_float(df["latitude"])
    df["longitude"] = to_float(df["longitude"])

    # Recalcular componentes temporales desde la marca normalizada (consistencia)
    df["crash_hour"] = df["crash_date"].dt.hour.astype("Int64")
    df["crash_month"] = df["crash_date"].dt.month.astype("Int64")
    # Convención SODA: 1 = domingo ... 7 = sábado
    df["crash_day_of_week"] = ((df["crash_date"].dt.dayofweek + 1) % 7 + 1).astype("Int64")

    lat, lon = df["latitude"], df["longitude"]
    reason = pd.Series(pd.NA, index=df.index, dtype="string")
    reason[lat.isna() | lon.isna()] = "missing_coordinates"
    reason[reason.isna() & (lat.abs() < 1e-6) & (lon.abs() < 1e-6)] = "zero_coordinates"
    reason[reason.isna() & ~in_bbox(lat, lon)] = "outside_chicago_bbox"

    quarantine = df.loc[reason.notna(), ["crash_record_id", "crash_date", "latitude", "longitude"]].copy()
    quarantine["reason"] = reason[reason.notna()]
    clean = df.loc[reason.isna()].copy()

    stats = {
        "raw": n_raw,
        "duplicates_removed": int(n_dupes),
        "quarantined": int(len(quarantine)),
        "quarantine_reasons": quarantine["reason"].value_counts().to_dict(),
        "clean": int(len(clean)),
    }
    return clean, quarantine, stats


def clean_vehicles(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n_raw = len(df)
    df = df.copy()
    for c in df.columns:
        df[c] = clean_str(df[c])
    df = df[df["crash_record_id"].notna() & df["crash_unit_id"].notna()]
    # Las unidades no motorizadas (peatones/ciclistas) no tienen vehicle_id en origen
    df["vehicle_id"] = df["vehicle_id"].fillna("U" + df["crash_unit_id"])
    df = df.drop_duplicates(["crash_record_id", "vehicle_id"], keep="last")
    df["unit_no"] = to_int(df["unit_no"])
    df["occupant_cnt"] = to_int(df["occupant_cnt"])
    df["vehicle_year"] = to_int(df["vehicle_year"])
    df.loc[~df["vehicle_year"].between(1900, datetime.now().year + 1), "vehicle_year"] = pd.NA
    df = df.drop(columns=["crash_unit_id"])
    return df, {"raw": n_raw, "duplicates_removed": int(n_raw - len(df)), "clean": int(len(df))}


def clean_people(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n_raw = len(df)
    df = df.copy()
    for c in df.columns:
        df[c] = clean_str(df[c])
    df = df[df["crash_record_id"].notna() & df["person_id"].notna()]
    df = df.drop_duplicates(["crash_record_id", "person_id"], keep="last")
    df["age"] = to_int(df["age"])
    df.loc[~df["age"].between(1, 110), "age"] = pd.NA
    df["sex"] = df["sex"].str.upper().where(df["sex"].str.upper().isin(VALID_SEX), pd.NA)
    return df, {"raw": n_raw, "duplicates_removed": int(n_raw - len(df)), "clean": int(len(df))}


def clean_permits(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n_raw = len(df)
    df = df.copy()
    for c in df.columns:
        df[c] = clean_str(df[c])
    out = pd.DataFrame({
        "permit_number": df["applicationnumber"],
        "work_type": df["worktype"],
        "work_type_description": df["worktypedescription"],
        "application_type": df["applicationtype"],
        "street_closure": df["streetclosure"],
        "application_start_date": to_ts(df["applicationstartdate"]),
        "issue_date": to_ts(df["applicationissueddate"]),
        "application_end_date": to_ts(df["applicationenddate"]),
        "street_number": df["streetnumberfrom"],
        "street_direction": df["direction"],
        "street_name": (df["streetname"].fillna("") + " " + df["suffix"].fillna("")).str.strip(),
        "work_description": df["comments"].str.slice(0, 500),
        "latitude": to_float(df["latitude"]),
        "longitude": to_float(df["longitude"]),
        "_status": df["applicationstatus"],
    })
    out = out[out["permit_number"].notna()]
    out = out[out["application_start_date"].notna() & out["application_end_date"].notna()]
    out = out[out["application_end_date"] >= out["application_start_date"]]
    # Permisos cancelados nunca generaron intervención física de la vía
    out = out[~out["_status"].fillna("").str.contains("Cancel", case=False)]
    out = out[in_bbox(out["latitude"], out["longitude"])]
    out = out.sort_values("issue_date").drop_duplicates("permit_number", keep="last").drop(columns="_status")
    return out, {"raw": n_raw, "discarded": int(n_raw - len(out)), "clean": int(len(out))}


def clean_aadt(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    n_raw = len(df)
    df = df.copy()
    for c in df.columns:
        df[c] = clean_str(df[c])
    out = pd.DataFrame({
        "traffic_volume_count_location_address": df["traffic_volume_count_location_address"],
        "street": df["street"],
        "date_of_count": to_ts(df["date_of_count"]),
        "total_passing_vehicle_volume": to_int(df["total_passing_vehicle_volume"]),
        "vehicle_volume_by_each_direction_of_traffic": df["vehicle_volume_by_each_direction_of_traffic"],
        "latitude": to_float(df["latitude"]),
        "longitude": to_float(df["longitude"]),
    })
    out = out[out["total_passing_vehicle_volume"].fillna(0) > 0]
    out = out[in_bbox(out["latitude"], out["longitude"])]
    out = out.drop_duplicates(["traffic_volume_count_location_address", "street", "date_of_count"])
    return out, {"raw": n_raw, "discarded": int(n_raw - len(out)), "clean": int(len(out))}


# ------------------------------------------------------------------------------
# Carga a PostGIS (COPY + upsert)
# ------------------------------------------------------------------------------
def _py(v):
    """Convierte escalares numpy/pandas a tipos nativos que psycopg sabe adaptar."""
    if v is None or v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and np.isnan(v):
        return None
    return v


def _records(df: pd.DataFrame):
    obj = df.astype(object).where(df.notna(), None)
    for row in obj.itertuples(index=False, name=None):
        yield tuple(_py(v) for v in row)


def copy_to_stage(cur: psycopg.Cursor, df: pd.DataFrame, target: str) -> str:
    stage = f"stage_{target}"
    cols = list(df.columns)
    cur.execute(f"DROP TABLE IF EXISTS {stage}")
    cur.execute(
        f"CREATE TEMP TABLE {stage} AS SELECT {', '.join(cols)} FROM {target} WITH NO DATA"
    )
    with cur.copy(f"COPY {stage} ({', '.join(cols)}) FROM STDIN") as cp:
        for rec in _records(df):
            cp.write_row(rec)
    return stage


GEOM_SQL = (
    "ST_SetSRID(ST_MakePoint(s.longitude, s.latitude), 4326)",
    "ST_Transform(ST_SetSRID(ST_MakePoint(s.longitude, s.latitude), 4326), 3435)",
)


def upsert(cur: psycopg.Cursor, df: pd.DataFrame, target: str, conflict: list[str] | None,
           with_geom: bool, require_parent: bool = False) -> int:
    stage = copy_to_stage(cur, df, target)
    cols = list(df.columns)
    insert_cols = cols + (["geom", "geom_3435"] if with_geom else [])
    select_cols = [f"s.{c}" for c in cols] + (list(GEOM_SQL) if with_geom else [])
    join = " JOIN silver_crashes p ON p.crash_record_id = s.crash_record_id" if require_parent else ""
    sql = f"INSERT INTO {target} ({', '.join(insert_cols)}) SELECT {', '.join(select_cols)} FROM {stage} s{join}"
    if conflict:
        updates = [c for c in insert_cols if c not in conflict]
        sql += f" ON CONFLICT ({', '.join(conflict)}) DO UPDATE SET " + ", ".join(f"{c} = EXCLUDED.{c}" for c in updates)
    cur.execute(sql)
    return cur.rowcount


def write_processed(df: pd.DataFrame, name: str) -> Path:
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    path = settings.processed_dir / f"silver_{name}.parquet"
    df.to_parquet(path, compression="snappy", index=False)
    return path


def run(datasets: list[str]) -> dict:
    report: dict = {"started_at": datetime.now(timezone.utc).isoformat(), "datasets": {}}
    with raw_connection() as conn:
        with conn.cursor() as cur:
            for ds in [d for d in LOAD_ORDER if d in datasets]:
                t0 = time.perf_counter()
                raw = read_bronze(ds)
                if ds == "crashes":
                    clean, quarantine, stats = clean_crashes(raw)
                    stats["loaded"] = upsert(cur, clean, "silver_crashes", ["crash_record_id"], with_geom=True)
                    if len(quarantine):
                        stage = copy_to_stage(cur, quarantine, "crashes_quarantine")
                        cur.execute(
                            f"INSERT INTO crashes_quarantine (crash_record_id, crash_date, latitude, longitude, reason) "
                            f"SELECT crash_record_id, crash_date, latitude, longitude, reason FROM {stage} "
                            f"ON CONFLICT (crash_record_id) DO UPDATE SET reason = EXCLUDED.reason, quarantined_at = now()"
                        )
                elif ds == "vehicles":
                    clean, stats = clean_vehicles(raw)
                    stats["loaded"] = upsert(cur, clean, "silver_vehicles", ["crash_record_id", "vehicle_id"],
                                             with_geom=False, require_parent=True)
                elif ds == "people":
                    clean, stats = clean_people(raw)
                    stats["loaded"] = upsert(cur, clean, "silver_people", ["crash_record_id", "person_id"],
                                             with_geom=False, require_parent=True)
                elif ds == "permits":
                    clean, stats = clean_permits(raw)
                    stats["loaded"] = upsert(cur, clean, "silver_road_permits", ["permit_number"], with_geom=True)
                elif ds == "aadt":
                    clean, stats = clean_aadt(raw)
                    cur.execute("TRUNCATE silver_traffic_counts RESTART IDENTITY")
                    stats["loaded"] = upsert(cur, clean, "silver_traffic_counts", None, with_geom=True)
                else:
                    raise ValueError(ds)
                conn.commit()
                write_processed(clean, ds)
                stats["success_rate"] = round(stats["loaded"] / stats["raw"], 4) if stats["raw"] else 1.0
                stats["elapsed_s"] = round(time.perf_counter() - t0, 1)
                report["datasets"][ds] = stats
                logger.info("[%s] %s", ds, stats)
    return report


def verify_integrity() -> dict:
    """Quality Gate de la Fase 2 sobre la base de datos ya cargada."""
    b = CHICAGO_BBOX
    checks = {}
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*), count(*) - count(DISTINCT crash_record_id) FROM silver_crashes")
        total, dupes = cur.fetchone()
        cur.execute(
            "SELECT count(*) FROM silver_crashes WHERE geom IS NULL OR NOT ST_IsValid(geom) OR ST_SRID(geom) <> 4326 "
            "OR NOT ST_Within(geom, ST_MakeEnvelope(%s, %s, %s, %s, 4326))",
            (b["min_lon"], b["min_lat"], b["max_lon"], b["max_lat"]),
        )
        invalid_geom = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM crashes_quarantine")
        quarantined = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FILTER (WHERE weather_condition IS NULL OR lighting_condition IS NULL "
            "OR posted_speed_limit IS NULL) FROM silver_crashes"
        )
        null_critical = cur.fetchone()[0]
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'silver_people' "
            "AND column_name IN ('city','zipcode','hospital','ems_agency','ems_run_no','drivers_license_class')"
        )
        pii_cols = [r[0] for r in cur.fetchall()]
        counts = {}
        for t in ("silver_vehicles", "silver_people", "silver_traffic_counts", "silver_road_permits"):
            cur.execute(f"SELECT count(*) FROM {t}")
            counts[t] = cur.fetchone()[0]
    checks = {
        "silver_crashes": total,
        **counts,
        "crashes_quarantine": quarantined,
        "duplicate_rate": round(dupes / total, 6) if total else 0.0,
        "invalid_or_outside_geom": invalid_geom,
        "null_critical_rate": round(null_critical / total, 4) if total else 0.0,
        "pii_columns_present": pii_cols,
    }
    checks["gate_passed"] = bool(
        total > 0 and checks["duplicate_rate"] < 0.01 and invalid_geom == 0
        and checks["null_critical_rate"] < 0.05 and not pii_cols
    )
    return checks


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Saneamiento y carga Bronze -> Silver")
    parser.add_argument("--datasets", nargs="+", default=LOAD_ORDER, choices=LOAD_ORDER)
    parser.add_argument("--verify-integrity", action="store_true", help="Ejecutar Quality Gate tras la carga")
    parser.add_argument("--verify-only", action="store_true", help="Sólo verificar, sin recargar")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    report = {} if args.verify_only else run(args.datasets)
    if args.verify_integrity or args.verify_only:
        report["integrity"] = verify_integrity()
        logger.info("Quality Gate Fase 2: %s", report["integrity"])
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    out = settings.processed_dir / "quality_report.json"
    previous = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    previous.update(report)
    out.write_text(json.dumps(previous, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
