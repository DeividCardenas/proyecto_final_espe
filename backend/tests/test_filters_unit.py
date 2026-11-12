"""El mismo filtro se traduce a PostGIS ($n) y a DuckDB (?) con idéntica semántica."""
from datetime import date

import duckdb
import pytest

from app.schemas.spatial import CrashFilters


def test_postgis_placeholders_are_sequential():
    f = CrashFilters(start_date=date(2024, 1, 1), end_date=date(2024, 2, 1), severity=[1, 2],
                     hour_from=7, hour_to=9, workzone_only=True)
    where, params = f.where("c")
    for i in range(1, len(params) + 1):
        assert f"${i}" in where
    assert f"${len(params) + 1}" not in where
    assert "c.active_workzone" in where and "ANY($" in where


def test_start_index_offsets_placeholders():
    where, params = CrashFilters().where("c", start_index=4)
    assert "$4" in where and "$7" in where and "$1," not in where
    assert len(params) == 4


def test_duckdb_placeholder_count_matches_params():
    f = CrashFilters(severity=[0, 2], hour_from=22, hour_to=3, end_date=date(2024, 5, 1))
    where, params = f.where(alias="", dialect="duckdb")
    assert where.count("?") == len(params)
    assert "$" not in where


def test_unknown_dialect_rejected():
    with pytest.raises(ValueError):
        CrashFilters().where(dialect="sqlite")


@pytest.fixture(scope="module")
def facts():
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE gold_crash_facts AS
        SELECT -87.65 + (i % 10) * 0.001 AS longitude, 41.85 + (i % 7) * 0.001 AS latitude,
               TIMESTAMP '2024-01-01 00:30:00' + INTERVAL (i) HOUR AS crash_date,
               (i % 24) AS crash_hour, (i % 3) AS severity, (i % 5 = 0) AS active_workzone
        FROM range(0, 24 * 60) t(i)
    """)
    yield con
    con.close()


def _count(con, f: CrashFilters) -> int:
    where, params = f.where(alias="", dialect="duckdb")
    return con.execute(f"SELECT count(*) FROM gold_crash_facts WHERE {where}", params).fetchone()[0]


def test_hour_range_crossing_midnight(facts):
    total = _count(facts, CrashFilters())
    night = _count(facts, CrashFilters(hour_from=22, hour_to=3))   # 22, 23, 0, 1, 2, 3
    assert night == total * 6 // 24
    day = _count(facts, CrashFilters(hour_from=4, hour_to=21))
    assert night + day == total


def test_end_date_is_inclusive(facts):
    one_day = _count(facts, CrashFilters(start_date=date(2024, 1, 2), end_date=date(2024, 1, 2)))
    assert one_day == 24


def test_severity_and_workzone(facts):
    total = _count(facts, CrashFilters())
    assert _count(facts, CrashFilters(severity=[2])) == total // 3
    assert _count(facts, CrashFilters(workzone_only=True)) == total // 5
