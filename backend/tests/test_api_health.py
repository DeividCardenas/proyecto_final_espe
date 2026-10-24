def test_health_ok(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "UP"
    assert body["database"]["connected"] is True
    assert body["database"]["postgis_version"].startswith("3.4")


def test_openapi_schema_valid(client):
    r = client.get("/api/v1/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for p in ("/api/v1/crashes/geojson", "/api/v1/predict/segment-risk", "/api/v1/analytics/kpis"):
        assert p in paths


def test_cors_header_for_allowed_origin(client):
    r = client.get("/api/v1/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
