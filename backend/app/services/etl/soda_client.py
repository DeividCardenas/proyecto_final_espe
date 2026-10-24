"""Cliente de ingesta SODA (Socrata) paginado, incremental y tolerante a fallos.

Descarga los datasets de Chicago Open Data a la Capa Bronze en formato Apache
Parquet (Snappy), un archivo por página en ``data/raw/<dataset>/``.

Uso:
    python -m app.services.etl.soda_client --dataset crashes --since 2023-01-01
    python -m app.services.etl.soda_client --dataset crashes --incremental
    python -m app.services.etl.soda_client --dataset aadt --all
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from app.core.config import settings

logger = logging.getLogger("etl.soda")


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    resource_id: str
    date_field: str | None
    columns: list[str]
    extra_where: str | None = None
    order: str = ":id"
    renames: dict[str, str] = field(default_factory=dict)


# Sólo se solicitan columnas útiles y sin PII (minimización de datos en origen).
DATASETS: dict[str, DatasetSpec] = {
    "crashes": DatasetSpec(
        key="crashes",
        resource_id="85ca-t3if",
        date_field="crash_date",
        columns=[
            "crash_record_id", "crash_date", "posted_speed_limit", "traffic_control_device",
            "device_condition", "weather_condition", "lighting_condition", "first_crash_type",
            "trafficway_type", "lane_cnt", "alignment", "roadway_surface_cond", "road_defect",
            "report_type", "crash_type", "intersection_related_i", "hit_and_run_i", "damage",
            "date_police_notified", "prim_contributory_cause", "sec_contributory_cause",
            "street_no", "street_direction", "street_name", "beat_of_occurrence", "work_zone_i",
            "num_units", "most_severe_injury", "injuries_total", "injuries_fatal",
            "injuries_incapacitating", "injuries_non_incapacitating",
            "injuries_reported_not_evident", "injuries_no_indication", "injuries_unknown",
            "crash_hour", "crash_day_of_week", "crash_month", "latitude", "longitude",
        ],
    ),
    "vehicles": DatasetSpec(
        key="vehicles",
        resource_id="68nd-jvt3",
        date_field="crash_date",
        columns=[
            "crash_unit_id", "crash_record_id", "unit_no", "unit_type", "vehicle_id", "make",
            "model", "vehicle_year", "vehicle_defect", "vehicle_type", "vehicle_use",
            "travel_direction", "maneuver", "occupant_cnt", "first_contact_point",
        ],
    ),
    "people": DatasetSpec(
        key="people",
        resource_id="u6pd-qa9d",
        date_field="crash_date",
        columns=[
            "person_id", "person_type", "crash_record_id", "vehicle_id", "seat_no", "state",
            "sex", "age", "safety_equipment", "airbag_deployed", "ejection",
            "injury_classification", "driver_action", "driver_vision", "physical_condition",
        ],
    ),
    "aadt": DatasetSpec(
        key="aadt",
        resource_id="pfsx-4n4m",
        date_field=None,
        columns=[
            "id", "traffic_volume_count_location_address", "street", "date_of_count",
            "total_passing_vehicle_volume", "vehicle_volume_by_each_direction_of_traffic",
            "latitude", "longitude",
        ],
    ),
    "permits": DatasetSpec(
        key="permits",
        resource_id="pubx-yq2d",
        date_field="applicationstartdate",
        columns=[
            "uniquekey", "applicationnumber", "applicationtype", "worktype",
            "worktypedescription", "applicationstatus", "applicationstartdate",
            "applicationenddate", "applicationissueddate", "streetnumberfrom", "direction",
            "streetname", "suffix", "streetclosure", "comments", "latitude", "longitude",
        ],
        # Sólo permisos que intervienen físicamente la vía (se excluyen mudanzas,
        # rodajes, fiestas de cuadra, eventos y permisos de sobrepeso).
        extra_where=(
            "latitude IS NOT NULL AND worktype NOT IN ('MovingVan','BlockParty','Filming',"
            "'Festival','Athletic','OWeight','OWeightAxl')"
        ),
    ),
}


class SodaClient:
    """Cliente HTTP con paginación limit/offset y backoff exponencial."""

    RETRY_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, domain: str | None = None, app_token: str | None = None,
                 page_size: int = 50_000, max_retries: int = 6, timeout: float = 120.0):
        self.base_url = f"https://{domain or settings.SOCRATA_DOMAIN}/resource"
        headers = {"Accept": "application/json"}
        token = app_token if app_token is not None else settings.SOCRATA_APP_TOKEN
        if token:
            headers["X-App-Token"] = token
        self.page_size = page_size
        self.max_retries = max_retries
        self._client = httpx.Client(headers=headers, timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self._client.close()

    def _get(self, resource_id: str, params: dict) -> list[dict]:
        url = f"{self.base_url}/{resource_id}.json"
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.get(url, params=params)
                if resp.status_code in self.RETRY_STATUS:
                    raise httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.json()
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status not in self.RETRY_STATUS:
                    raise
                if attempt == self.max_retries:
                    raise
                wait = min(2 ** attempt, 60)
                logger.warning("Fallo SODA (%s). Reintento %d/%d en %ss", exc, attempt + 1, self.max_retries, wait)
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def count(self, spec: DatasetSpec, where: str | None) -> int:
        params = {"$select": "count(*) AS n"}
        if where:
            params["$where"] = where
        rows = self._get(spec.resource_id, params)
        return int(rows[0]["n"]) if rows else 0

    def iter_pages(self, spec: DatasetSpec, where: str | None, limit: int | None):
        offset = 0
        fetched = 0
        while True:
            page = self.page_size if limit is None else min(self.page_size, limit - fetched)
            if page <= 0:
                break
            params = {
                "$select": ",".join(spec.columns),
                "$order": spec.order,
                "$limit": page,
                "$offset": offset,
            }
            if where:
                params["$where"] = where
            rows = self._get(spec.resource_id, params)
            if not rows:
                break
            yield rows
            fetched += len(rows)
            offset += len(rows)
            if len(rows) < page:
                break


def _watermark_path(dataset_dir: Path) -> Path:
    return dataset_dir / "_watermark.json"


def read_watermark(dataset_dir: Path) -> str | None:
    p = _watermark_path(dataset_dir)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("max_value")
    return None


def build_where(spec: DatasetSpec, since: str | None, watermark: str | None) -> str | None:
    clauses = []
    if spec.extra_where:
        clauses.append(f"({spec.extra_where})")
    if spec.date_field:
        if watermark:
            clauses.append(f"{spec.date_field} > '{watermark}'")
        elif since:
            clauses.append(f"{spec.date_field} >= '{since}T00:00:00'")
    return " AND ".join(clauses) if clauses else None


def ingest(dataset: str, since: str | None = None, limit: int | None = None,
           incremental: bool = False, page_size: int = 50_000, client: SodaClient | None = None) -> dict:
    spec = DATASETS[dataset]
    out_dir = settings.raw_dir / spec.key
    watermark = read_watermark(out_dir) if incremental else None
    if not incremental and out_dir.exists():
        shutil.rmtree(out_dir)  # Carga completa: se reemplaza la Capa Bronze del dataset
    out_dir.mkdir(parents=True, exist_ok=True)

    where = build_where(spec, since, watermark)
    owns_client = client is None
    client = client or SodaClient(page_size=page_size)
    started = time.perf_counter()
    try:
        expected = client.count(spec, where)
        target = expected if limit is None else min(expected, limit)
        logger.info("[%s] %s registros disponibles (descargando %s). where=%s", dataset, expected, target, where)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        total = 0
        max_value = watermark
        for i, rows in enumerate(client.iter_pages(spec, where, limit)):
            df = pd.DataFrame.from_records(rows)
            # Las columnas ausentes en una página (todas nulas) se materializan igual
            for col in spec.columns:
                if col not in df.columns:
                    df[col] = None
            df = df[spec.columns].astype("string")
            df.to_parquet(out_dir / f"part-{stamp}-{i:05d}.parquet", compression="snappy", index=False)
            total += len(df)
            if spec.date_field and spec.date_field in df.columns:
                page_max = df[spec.date_field].dropna().max()
                if page_max is not pd.NA and page_max is not None and (max_value is None or page_max > max_value):
                    max_value = str(page_max)
            logger.info("[%s] página %d: %d filas (acumulado %d/%d)", dataset, i, len(df), total, target)
    finally:
        if owns_client:
            client.close()

    elapsed = time.perf_counter() - started
    summary = {
        "dataset": dataset,
        "resource_id": spec.resource_id,
        "where": where,
        "expected": target,
        "downloaded": total,
        "success_rate": round(total / target, 4) if target else 1.0,
        "max_value": max_value,
        "elapsed_s": round(elapsed, 1),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    _watermark_path(out_dir).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("[%s] completado: %s", dataset, summary)
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingesta SODA -> Capa Bronze (Parquet)")
    parser.add_argument("--dataset", required=True, choices=[*DATASETS.keys(), "all"])
    parser.add_argument("--since", default="2023-01-01", help="Fecha mínima (YYYY-MM-DD) para datasets con fecha")
    parser.add_argument("--limit", type=int, default=None, help="Máximo de registros a descargar")
    parser.add_argument("--all", action="store_true", help="Descargar todo el histórico (ignora --since)")
    parser.add_argument("--incremental", action="store_true", help="Sólo registros posteriores a la marca de agua")
    parser.add_argument("--page-size", type=int, default=50_000)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    since = None if args.all else args.since
    keys = list(DATASETS) if args.dataset == "all" else [args.dataset]
    for key in keys:
        ingest(key, since=since, limit=args.limit, incremental=args.incremental, page_size=args.page_size)


if __name__ == "__main__":
    main()
