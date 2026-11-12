"""Pruebas unitarias de la API sin base de datos: arranque tolerante, códigos de
error, validación de parámetros y caché HTTP."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.api.v1.endpoints.health as health
import app.core.database as database
import app.main as main
from app.core.config import settings


@pytest.fixture()
def offline_client(monkeypatch, tmp_path):
    """Cliente con PostGIS inaccesible y sin capa Gold."""

    async def refuse(*args, **kwargs):
        raise ConnectionRefusedError("PostGIS apagado")

    monkeypatch.setattr(database, "_pool", None)
    monkeypatch.setattr(database, "init_db_pool", refuse)
    monkeypatch.setattr(main, "init_db_pool", refuse)
    monkeypatch.setattr(settings, "DUCKDB_PATH", str(tmp_path / "no_existe.duckdb"))
    with TestClient(main.app, raise_server_exceptions=False) as c:
        yield c


def test_api_starts_without_database(offline_client):
    assert offline_client.get("/api/v1/live").json() == {"status": "UP"}


def test_health_is_503_when_database_is_down(offline_client):
    r = offline_client.get("/api/v1/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "DEGRADED" and body["database"]["connected"] is False
    assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("path", [
    "/api/v1/crashes/geojson",
    "/api/v1/permits/active",
    "/api/v1/traffic/stations",
    "/api/v1/tiles/crashes/12/1050/1522.pbf",
])
def test_postgis_endpoints_answer_503_json(offline_client, path):
    r = offline_client.get(path)
    assert r.status_code == 503
    assert "no disponible" in r.json()["detail"]
    assert r.headers.get("retry-after") == "5"


@pytest.mark.parametrize("path", [
    "/api/v1/analytics/kpis",
    "/api/v1/analytics/hourly-distribution",
    "/api/v1/risk/grid",
    "/api/v1/risk/segments",
    "/api/v1/risk/segment-distribution",
])
def test_gold_endpoints_answer_503_without_duckdb(offline_client, path):
    r = offline_client.get(path)
    assert r.status_code == 503
    assert "DuckDB" in r.json()["detail"]


def test_responses_carry_request_id(offline_client):
    r = offline_client.get("/api/v1/live", headers={"X-Request-ID": "abc123"})
    assert r.headers["x-request-id"] == "abc123"
    assert r.headers["server-timing"].startswith("app;dur=")


@pytest.mark.parametrize("params", [
    {"min_lon": -87.6, "max_lon": -87.7},               # bbox invertido
    {"severity": 5},                                     # clase inexistente
    {"start_date": "2025-02-01", "end_date": "2025-01-01"},
    {"hour_from": 24},
])
def test_invalid_crash_filters_rejected_before_touching_db(offline_client, params):
    assert offline_client.get("/api/v1/crashes/geojson", params=params).status_code == 422


def test_tile_out_of_range_is_404(offline_client):
    assert offline_client.get("/api/v1/tiles/crashes/3/8/1.pbf").status_code == 404


def test_stream_and_cluster_limits(offline_client):
    assert offline_client.get("/api/v1/crashes/stream", params={"limit": 1_000_000}).status_code == 422
    assert offline_client.get("/api/v1/crashes/clusters", params={"sample": 500_000}).status_code == 422


def test_crash_detail_id_length_is_bounded(offline_client):
    assert offline_client.get("/api/v1/crashes/" + "x" * 200).status_code == 422


def test_health_probe_never_raises(monkeypatch, offline_client):
    async def slow():
        raise TimeoutError

    monkeypatch.setattr(health, "_db_probe", slow)
    assert offline_client.get("/api/v1/health").status_code == 503
