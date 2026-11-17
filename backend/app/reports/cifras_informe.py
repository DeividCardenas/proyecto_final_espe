"""Cifras del informe de resultados y del póster, calculadas desde la capa Silver.

Uso (con PostGIS cargado):

    docker compose run --rm etl python -m app.reports.cifras_informe

Escribe ``data/processed/cifras_informe.json``. El informe (docs/INFORME_RESULTADOS.md)
y el póster citan este archivo, así que cada cifra es reproducible con un solo comando.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import raw_connection
from app.core.severity import GRID_SIZE_FT

SPEEDS = (15, 20, 25, 30, 35, 40)


def _one(cur, sql: str, params: tuple = ()):
    cur.execute(sql, params)
    return cur.fetchone()


def _all(cur, sql: str, params: tuple = ()):
    cur.execute(sql, params)
    return cur.fetchall()


def _rate(n: int, total: int) -> float | None:
    return round(n / total, 5) if total else None


def compute() -> dict:
    out: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}
    with raw_connection() as conn, conn.cursor() as cur:
        n, d0, d1, crit, fatal_people, fatal_crashes = _one(cur, """
            SELECT count(*), min(crash_date), max(crash_date),
                   count(*) FILTER (WHERE severity = 2),
                   coalesce(sum(injuries_fatal), 0),
                   count(*) FILTER (WHERE injuries_fatal > 0)
            FROM silver_crashes""")
        out["crashes"] = {
            "n": n, "date_min": d0.isoformat() if d0 else None, "date_max": d1.isoformat() if d1 else None,
            "critical": crit, "critical_rate": _rate(crit, n),
            "fatalities": int(fatal_people), "fatal_crashes": fatal_crashes,
        }
        out["silver_counts"] = {
            t: _one(cur, f"SELECT count(*) FROM {t}")[0]
            for t in ("silver_crashes", "silver_vehicles", "silver_people",
                      "silver_road_permits", "silver_traffic_counts", "crashes_quarantine")
        }

        # Enriquecimiento
        imp, wz = _one(cur, """
            SELECT count(*) FILTER (WHERE aadt_imputed), count(*) FILTER (WHERE active_workzone)
            FROM silver_crashes""")
        out["enrichment"] = {"aadt_imputed_rate": _rate(imp, n), "active_workzone_rate": _rate(wz, n)}

        # Usuarios vulnerables (tipo de primera colisión)
        out["vulnerable"] = {
            ct: dict(zip(("n", "critical"), _one(cur, """
                SELECT count(*), count(*) FILTER (WHERE severity = 2)
                FROM silver_crashes WHERE first_crash_type = %s""", (ct,))))
            for ct in ("PEDESTRIAN", "PEDALCYCLIST")
        }
        for v in out["vulnerable"].values():
            v["critical_rate"] = _rate(v["critical"], v["n"])

        # Velocidad señalizada
        out["speed"] = []
        for sp, cnt, c in _all(cur, """
                SELECT posted_speed_limit, count(*), count(*) FILTER (WHERE severity = 2)
                FROM silver_crashes WHERE posted_speed_limit = ANY(%s)
                GROUP BY 1 ORDER BY 1""", (list(SPEEDS),)):
            out["speed"].append({"mph": sp, "n": cnt, "critical": c, "critical_rate": _rate(c, cnt)})

        # Iluminación
        out["lighting"] = [
            {"lighting": l, "n": cnt, "critical": c, "critical_rate": _rate(c, cnt)}
            for l, cnt, c in _all(cur, """
                SELECT lighting_condition, count(*), count(*) FILTER (WHERE severity = 2)
                FROM silver_crashes GROUP BY 1 ORDER BY 2 DESC""")
        ]

        # Corredores por siniestros críticos
        out["corridors"] = [
            {"street": s, "critical": c, "fatalities": int(f), "crashes": cnt}
            for s, c, f, cnt in _all(cur, """
                SELECT street_name, count(*) FILTER (WHERE severity = 2),
                       coalesce(sum(injuries_fatal), 0), count(*)
                FROM silver_crashes WHERE street_name IS NOT NULL
                GROUP BY 1 ORDER BY 2 DESC LIMIT 10""")
        ]

        # Obras con cierre de calzada
        out["workzone"] = [
            {"active_workzone": w, "n": cnt, "critical": c, "critical_rate": _rate(c, cnt)}
            for w, cnt, c in _all(cur, """
                SELECT active_workzone, count(*), count(*) FILTER (WHERE severity = 2)
                FROM silver_crashes GROUP BY 1 ORDER BY 1""")
        ]

        # Celdas de 500 m de alto riesgo (>= 30 siniestros y tasa crítica >= 3 %)
        cells, = _one(cur, f"""
            SELECT count(*) FROM (
                SELECT floor(ST_X(geom_3435) / {GRID_SIZE_FT}) gx, floor(ST_Y(geom_3435) / {GRID_SIZE_FT}) gy,
                       count(*) n, avg((severity = 2)::int) r
                FROM silver_crashes WHERE geom_3435 IS NOT NULL GROUP BY 1, 2
            ) t WHERE n >= 30 AND r >= 0.03""")
        out["high_risk_cells"] = cells

    qr = settings.processed_dir / "quality_report.json"
    if qr.exists():
        out["quality_report"] = json.loads(qr.read_text(encoding="utf-8"))
    return out


def main() -> None:
    data = compute()
    path = settings.processed_dir / "cifras_informe.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "quality_report"}, ensure_ascii=False, indent=1, default=str))
    print(f"\nEscrito en {path}")


if __name__ == "__main__":
    main()
