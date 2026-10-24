import time

import psycopg
import pytest

from app.core.config import CHICAGO_BBOX
from app.core.database import raw_connection

LOOP = {"min_lon": -87.65, "min_lat": 41.85, "max_lon": -87.60, "max_lat": 41.90}


def test_geojson_bbox_contains_only_points_inside(client):
    r = client.get("/api/v1/crashes/geojson", params={**LOOP, "limit": 2000})
    assert r.status_code == 200
    fc = r.json()
    assert fc["type"] == "FeatureCollection" and fc["features"]
    for feat in fc["features"]:
        lon, lat = feat["geometry"]["coordinates"]
        assert LOOP["min_lon"] <= lon <= LOOP["max_lon"] and LOOP["min_lat"] <= lat <= LOOP["max_lat"]


def test_geojson_bbox_latency_under_100ms(client):
    params = {**LOOP, "limit": 1000}
    client.get("/api/v1/crashes/geojson", params=params)  # calentamiento de caché
    t0 = time.perf_counter()
    r = client.get("/api/v1/crashes/geojson", params=params)
    assert r.status_code == 200
    assert (time.perf_counter() - t0) < 0.1


def test_severity_filter(client):
    r = client.get("/api/v1/crashes/geojson", params={**LOOP, "severity": 2, "limit": 500})
    feats = r.json()["features"]
    assert feats and all(f["properties"]["severity"] == 2 for f in feats)


def test_invalid_bbox_rejected(client):
    r = client.get("/api/v1/crashes/geojson", params={"min_lon": -87.6, "max_lon": -87.7})
    assert r.status_code == 422


def test_all_crash_geometries_inside_chicago():
    b = CHICAGO_BBOX
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM silver_crashes WHERE NOT ST_Within(geom, ST_MakeEnvelope(%s,%s,%s,%s,4326))",
            (b["min_lon"], b["min_lat"], b["max_lon"], b["max_lat"]))
        assert cur.fetchone()[0] == 0


def test_buffer_is_metric_250m():
    """820.21 pies de topógrafo en EPSG:3435 equivalen a 250 m geodésicos (error < 1%)."""
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            WITH p AS (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(-87.6298, 41.8781), 4326), 3435) g)
            SELECT ST_Distance(ST_Transform(p.g, 4326)::geography,
                               ST_Transform(ST_Translate(p.g, 820.21, 0), 4326)::geography)
            FROM p
        """)
        meters = cur.fetchone()[0]
    assert abs(meters - 250) / 250 < 0.01


def test_gist_index_used_for_bbox():
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("SET enable_seqscan = off")
        cur.execute("EXPLAIN SELECT 1 FROM silver_crashes "
                    "WHERE geom && ST_MakeEnvelope(-87.65, 41.85, -87.60, 41.90, 4326)")
        plan = "\n".join(r[0] for r in cur.fetchall())
    assert "idx_crashes_geom" in plan


def test_no_duplicate_gist_indexes():
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT tablename, substring(indexdef from 'USING gist \\((.*)\\)') AS col, count(*)
            FROM pg_indexes WHERE schemaname = 'public' AND indexdef ILIKE '%using gist%'
            GROUP BY 1, 2 HAVING count(*) > 1
        """)
        assert cur.fetchall() == []


def test_foreign_key_rejects_orphans():
    with raw_connection() as conn, conn.cursor() as cur:
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            cur.execute("INSERT INTO silver_vehicles (crash_record_id, vehicle_id) VALUES ('no-existe', 'x')")
        conn.rollback()


def test_hotspots_and_permits(client):
    r = client.get("/api/v1/crashes/clusters", params=LOOP)
    assert r.status_code == 200 and r.json()["features"]
    r = client.get("/api/v1/permits/active", params={**LOOP, "limit": 50})
    assert r.status_code == 200 and r.json()["type"] == "FeatureCollection"


def test_analytics_kpis(client):
    k = client.get("/api/v1/analytics/kpis").json()
    assert k["total_crashes"] > 0 and 0 <= k["critical_rate"] <= 1
    hours = client.get("/api/v1/analytics/hourly-distribution").json()
    assert {h["hour"] for h in hours} == set(range(24))
