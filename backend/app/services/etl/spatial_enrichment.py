"""Enriquecimiento topológico espaciotemporal sobre la Capa Silver (PostGIS).

1. Volumen de tráfico AADT: estación de aforo más cercana (KNN ``<->`` sobre el
   índice GiST en EPSG:3435) dentro de un radio de 500 m; si no hay sensor
   próximo se imputa el promedio de las estaciones.
2. Obras viales CDOT activas: permiso vigente en la fecha del siniestro dentro de
   un buffer métrico (por defecto 250 m) calculado en EPSG:3435 (pies de topógrafo).
3. Optimización física: ``CLUSTER`` por índice espacial y ``ANALYZE``.

Uso:
    python -m app.services.etl.spatial_enrichment --buffer-meters 250
"""
from __future__ import annotations

import argparse
import json
import logging
import time

from app.core.config import settings
from app.core.database import raw_connection

logger = logging.getLogger("etl.spatial")

US_SURVEY_FT_PER_M = 3.280833333  # EPSG:3435 usa pies de topógrafo de EE.UU.


def meters_to_survey_ft(m: float) -> float:
    return round(m * US_SURVEY_FT_PER_M, 2)


AADT_SQL = """
WITH nn AS (
    SELECT c.crash_record_id, t.total_passing_vehicle_volume AS vol, t.dist_ft
    FROM silver_crashes c
    CROSS JOIN LATERAL (
        SELECT tc.total_passing_vehicle_volume,
               c.geom_3435 <-> tc.geom_3435 AS dist_ft
        FROM silver_traffic_counts tc
        ORDER BY c.geom_3435 <-> tc.geom_3435
        LIMIT 1
    ) t
    WHERE c.geom_3435 IS NOT NULL
)
UPDATE silver_crashes c
SET aadt_volume = CASE WHEN nn.dist_ft <= %(radius_ft)s THEN nn.vol ELSE %(fallback)s END,
    aadt_distance_m = nn.dist_ft / %(ft_per_m)s,
    aadt_imputed = nn.dist_ft > %(radius_ft)s
FROM nn
WHERE nn.crash_record_id = c.crash_record_id
"""

# Se elige, por siniestro, el permiso vigente más cercano dentro del buffer.
# Hallazgo: con todos los permisos (aperturas de servicios públicos, ocupación de
# acera...) el 89% de los siniestros caía en "zona de obra", una variable saturada
# sin poder discriminante; por eso se exige afectación real de la calzada.
# ST_DWithin sobre geom_3435 usa el índice GiST idx_permits_geom_3435.
WORKZONE_SQL = """
WITH hit AS (
    SELECT c.crash_record_id, w.permit_number
    FROM silver_crashes c
    CROSS JOIN LATERAL (
        SELECT p.permit_number
        FROM silver_road_permits p
        WHERE ST_DWithin(c.geom_3435, p.geom_3435, %(buffer_ft)s)
          AND c.crash_date BETWEEN p.application_start_date AND p.application_end_date
          -- Sólo permisos con cierre total o parcial de la calzada
          AND p.street_closure IN ('Full', 'Partial')
        ORDER BY c.geom_3435 <-> p.geom_3435
        LIMIT 1
    ) w
    WHERE c.geom_3435 IS NOT NULL
)
UPDATE silver_crashes c
SET active_workzone = true,
    workzone_permit_id = hit.permit_number
FROM hit
WHERE hit.crash_record_id = c.crash_record_id
"""


def enrich(buffer_meters: float = 250.0, aadt_radius_meters: float = 500.0, cluster: bool = True) -> dict:
    buffer_ft = meters_to_survey_ft(buffer_meters)
    radius_ft = meters_to_survey_ft(aadt_radius_meters)
    stats: dict = {"buffer_meters": buffer_meters, "buffer_survey_ft": buffer_ft,
                   "aadt_radius_meters": aadt_radius_meters}
    with raw_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SET work_mem = '256MB'")
            # Asegura geometría proyectada para filas cargadas por otras vías
            cur.execute(
                "UPDATE silver_crashes SET geom_3435 = ST_Transform(geom, 3435) "
                "WHERE geom IS NOT NULL AND geom_3435 IS NULL"
            )

            t0 = time.perf_counter()
            cur.execute("SELECT round(avg(total_passing_vehicle_volume))::int FROM silver_traffic_counts")
            fallback = cur.fetchone()[0]
            if fallback is None:
                raise RuntimeError("silver_traffic_counts está vacía: ejecute la ingesta del dataset 'aadt'")
            cur.execute(AADT_SQL, {"radius_ft": radius_ft, "fallback": fallback, "ft_per_m": US_SURVEY_FT_PER_M})
            stats["aadt_updated"] = cur.rowcount
            stats["aadt_fallback_volume"] = fallback
            stats["aadt_elapsed_s"] = round(time.perf_counter() - t0, 1)
            conn.commit()
            logger.info("AADT asignado a %s siniestros (%.1fs)", stats["aadt_updated"], stats["aadt_elapsed_s"])

            t0 = time.perf_counter()
            cur.execute("UPDATE silver_crashes SET active_workzone = false, workzone_permit_id = NULL "
                        "WHERE active_workzone OR workzone_permit_id IS NOT NULL")
            cur.execute(WORKZONE_SQL, {"buffer_ft": buffer_ft})
            stats["workzone_crashes"] = cur.rowcount
            stats["workzone_elapsed_s"] = round(time.perf_counter() - t0, 1)
            conn.commit()
            logger.info("Siniestros en zona de obra activa: %s (%.1fs)", stats["workzone_crashes"],
                        stats["workzone_elapsed_s"])

            cur.execute("""
                SELECT count(*),
                       count(*) FILTER (WHERE aadt_imputed),
                       count(*) FILTER (WHERE active_workzone),
                       count(*) FILTER (WHERE work_zone_i),
                       count(*) FILTER (WHERE work_zone_i AND active_workzone)
                FROM silver_crashes
            """)
            total, imputed, wz, police_wz, both = cur.fetchone()
            stats.update({
                "crashes_total": total,
                "aadt_imputed_rate": round(imputed / total, 4) if total else 0,
                "workzone_rate": round(wz / total, 4) if total else 0,
                "police_reported_workzone": police_wz,
                "police_workzone_matched_by_permit": both,
            })

        conn.commit()
        if cluster:
            # CLUSTER/ANALYZE fuera de transacción explícita
            conn.autocommit = True
            with conn.cursor() as cur:
                t0 = time.perf_counter()
                for table, idx in (("silver_crashes", "idx_crashes_geom"),
                                   ("silver_road_permits", "idx_permits_geom"),
                                   ("silver_traffic_counts", "idx_traffic_geom")):
                    cur.execute(f"CLUSTER {table} USING {idx}")
                    cur.execute(f"ANALYZE {table}")
                cur.execute("ANALYZE silver_vehicles")
                cur.execute("ANALYZE silver_people")
                stats["cluster_elapsed_s"] = round(time.perf_counter() - t0, 1)
    logger.info("Enriquecimiento completado: %s", stats)
    return stats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Enriquecimiento topológico Silver")
    parser.add_argument("--buffer-meters", type=float, default=250.0)
    parser.add_argument("--aadt-radius-meters", type=float, default=500.0)
    parser.add_argument("--no-cluster", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stats = enrich(args.buffer_meters, args.aadt_radius_meters, cluster=not args.no_cluster)

    out = settings.processed_dir / "quality_report.json"
    report = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    report["enrichment"] = stats
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
