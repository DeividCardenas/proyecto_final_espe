"""Fixtures compartidas. Las pruebas de integración requieren PostGIS con datos
cargados (ejecutar dentro del contenedor: docker compose run --rm etl pytest)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:  # ejecuta el lifespan (pool asyncpg + modelo)
        yield c
