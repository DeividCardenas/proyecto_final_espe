"""Capa Gold: las escrituras reemplazan el archivo de forma atómica y nunca chocan
con la conexión de sólo lectura que mantiene la API."""
from __future__ import annotations

import threading

import duckdb
import pandas as pd
import pytest

from app.core.config import settings
from app.core.errors import OlapUnavailableError
from app.services.olap import duckdb_engine


@pytest.fixture()
def gold(tmp_path, monkeypatch):
    path = tmp_path / "gold.duckdb"
    monkeypatch.setattr(settings, "DUCKDB_PATH", str(path))
    duckdb_engine._reader.invalidate()
    with duckdb.connect(str(path)) as con:
        con.execute("CREATE TABLE t AS SELECT 1 AS v")
    yield path
    duckdb_engine._reader.invalidate()


def test_missing_file_raises_olap_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DUCKDB_PATH", str(tmp_path / "nada.duckdb"))
    duckdb_engine._reader.invalidate()
    with pytest.raises(OlapUnavailableError):
        duckdb_engine.query("SELECT 1")


def test_attach_table_while_api_reads(gold):
    # La API ya tiene el archivo abierto en sólo lectura (antes: IOException por bloqueo)
    assert duckdb_engine.query("SELECT v FROM t") == [{"v": 1}]
    duckdb_engine.attach_table("gold_segment_risk", pd.DataFrame({"segment_id": ["A"], "p_alto": [0.4]}))
    assert duckdb_engine.table_exists("gold_segment_risk")
    # Las tablas previas se conservan en la copia publicada
    assert duckdb_engine.query("SELECT v FROM t") == [{"v": 1}]
    assert not list(gold.parent.glob("*.tmp*"))


def test_reader_picks_up_replaced_file(gold):
    assert duckdb_engine.query("SELECT v FROM t")[0]["v"] == 1
    duckdb_engine.attach_table("t", pd.DataFrame({"v": [2]}))
    assert duckdb_engine.query("SELECT v FROM t")[0]["v"] == 2


def test_attach_rejects_unsafe_table_names(gold):
    with pytest.raises(ValueError):
        duckdb_engine.attach_table("t; DROP TABLE t", pd.DataFrame({"v": [1]}))


def test_concurrent_reads_share_connection(gold):
    errors: list[Exception] = []

    def work():
        try:
            for _ in range(20):
                assert duckdb_engine.query("SELECT count(*) AS n FROM t")[0]["n"] == 1
        except Exception as exc:  # pragma: no cover - sólo si falla
            errors.append(exc)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert errors == []
