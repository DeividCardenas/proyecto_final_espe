import time

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core.http_cache import TTLCache, cached_bytes_response, dumps


def test_ttl_cache_expires_and_evicts():
    c = TTLCache(maxsize=2, ttl=0.05)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)
    assert c.get("a") is None and c.get("c") == 3
    time.sleep(0.06)
    assert c.get("c") is None


def test_etag_and_304():
    app = FastAPI()
    body = dumps({"x": "ñ", "n": 1})

    @app.get("/r")
    def r(request: Request):
        return cached_bytes_response(request, body, max_age=60)

    client = TestClient(app)
    first = client.get("/r")
    assert first.status_code == 200 and first.json() == {"x": "ñ", "n": 1}
    assert first.headers["cache-control"] == "public, max-age=60"
    again = client.get("/r", headers={"If-None-Match": first.headers["etag"]})
    assert again.status_code == 304 and again.content == b""
