"""Fixtures compartidas.

* Pruebas unitarias: no necesitan base de datos (`pytest -m "not integration"`).
* Pruebas de integración (`@pytest.mark.integration`): requieren PostGIS con datos
  (reales o los sintéticos de ``tests/fixtures/seed_synthetic.sql``). Si la BD no
  responde se marcan como saltadas en lugar de fallar.

Ejecución completa dentro de Docker: ``docker compose run --rm etl pytest``.
"""
from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def _db_available() -> bool:
    try:
        with psycopg.connect(settings.psycopg_dsn, connect_timeout=3) as conn:
            conn.execute("SELECT 1 FROM silver_crashes LIMIT 1")
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items):
    if not any(item.get_closest_marker("integration") for item in items):
        return
    if _db_available():
        return
    skip = pytest.mark.skip(reason="PostGIS no disponible o sin tablas (prueba de integración)")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip)


@pytest.fixture(scope="session")
def client():
    # Ejecuta el lifespan: pool asyncpg (tolerante si la BD no responde) + modelo
    with TestClient(app) as c:
        yield c
