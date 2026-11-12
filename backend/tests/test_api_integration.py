"""Integración con PostGIS + capa Gold: contratos nuevos de la revisión del backend."""
from __future__ import annotations

import json

import pytest

from app.core.database import raw_connection

pytestmark = pytest.mark.integration

LOOP = {"min_lon": -87.70, "min_lat": 41.80, "max_lon": -87.55, "max_lat": 41.95}


def _pg_count(where: str = "TRUE") -> int:
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM silver_crashes WHERE geom IS NOT NULL AND {where}")
        return cur.fetchone()[0]


def test_hour_range_crossing_midnight_geojson(client):
    r = client.get("/api/v1/crashes/geojson", params={**LOOP, "hour_from": 22, "hour_to": 3, "limit": 3000})
    hours = {f["properties"]["hour"] for f in r.json()["features"]}
    assert hours and hours <= {22, 23, 0, 1, 2, 3}


def test_kpis_agree_with_postgis(client):
    k = client.get("/api/v1/analytics/kpis").json()
    assert k["total_crashes"] == _pg_count()
    night = client.get("/api/v1/analytics/kpis", params={"hour_from": 22, "hour_to": 3}).json()
    assert night["total_crashes"] == _pg_count("(crash_hour >= 22 OR crash_hour <= 3)")
    assert set(k) >= {"yoy_change", "high_risk_cells", "critical_rate", "first_date", "last_date"}


def test_tiles_workzone_filter_and_content_type(client):
    full = client.get("/api/v1/tiles/crashes/11/525/761.pbf")
    wz = client.get("/api/v1/tiles/crashes/11/525/761.pbf", params={"workzone_only": "true"})
    assert full.headers["content-type"] == "application/vnd.mapbox-vector-tile"
    assert 0 < len(wz.content) < len(full.content)
    detail = client.get("/api/v1/tiles/crashes/14/4202/6091.pbf", params={"workzone_only": "true"})
    assert detail.status_code == 200


def test_stream_ndjson_respects_limit(client):
    with client.stream("GET", "/api/v1/crashes/stream", params={"limit": 2500}) as r:
        lines = [line for line in r.iter_lines() if line]
    assert r.status_code == 200 and len(lines) == 2500
    assert {"lon", "lat", "severity"} <= set(json.loads(lines[0]))


def test_crash_detail_404(client):
    r = client.get("/api/v1/crashes/NO-EXISTE")
    assert r.status_code == 404 and r.json()["detail"] == "Siniestro no encontrado"


def test_permits_bbox_validation(client):
    assert client.get("/api/v1/permits/active", params={"min_lon": -87.5, "max_lon": -87.6}).status_code == 422


def test_clusters_cached_with_etag(client):
    first = client.get("/api/v1/crashes/clusters", params=LOOP)
    assert first.status_code == 200 and "etag" in first.headers
    again = client.get("/api/v1/crashes/clusters", params=LOOP, headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304


def test_risk_grid_etag_roundtrip(client):
    r = client.get("/api/v1/risk/grid")
    assert r.status_code == 200 and r.json()["type"] == "FeatureCollection"
    assert client.get("/api/v1/risk/grid", headers={"If-None-Match": r.headers["etag"]}).status_code == 304


def test_prediction_context_uses_current_history(client):
    body = client.post("/api/v1/predict/segment-risk", json={"coordinates": [-87.6298, 41.8781]}).json()
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT greatest(extract(epoch FROM max(crash_date) - min(crash_date)) / (365.25*86400), 1.0) "
                    "FROM silver_crashes WHERE geom IS NOT NULL AND crash_date IS NOT NULL")
        years = float(cur.fetchone()[0])
    assert body["context"]["history_years"] == pytest.approx(years, abs=0.01)
    assert body["model"]["mode"] in ("ml", "heuristic_fallback")


def test_simulator_rejects_unknown_category(client):
    r = client.post("/api/v1/predict/segment-risk",
                    json={"coordinates": [-87.6298, 41.8781], "first_crash_type": "REAR-END"})
    assert r.status_code == 422
