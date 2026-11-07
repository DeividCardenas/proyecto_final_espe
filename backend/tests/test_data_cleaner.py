import pandas as pd

from app.services.etl.data_cleaner import clean_crashes, clean_people
from app.services.etl.soda_client import DATASETS, build_where

FIXED = ("crash_record_id", "crash_date", "date_police_notified", "latitude", "longitude")


def _crash(cid, lat, lon, date="2024-05-01T10:00:00.000"):
    row = {c: None for c in DATASETS["crashes"].columns if c not in FIXED}
    row.update({"crash_record_id": cid, "crash_date": date, "date_police_notified": date,
                "latitude": lat, "longitude": lon})
    return row


def test_quarantine_and_dedup():
    df = pd.DataFrame([
        _crash("a", "41.88", "-87.63"),
        _crash("a", "41.88", "-87.63"),           # duplicado
        _crash("b", "0", "0"),                    # coordenadas (0,0)
        _crash("c", None, None),                  # sin coordenadas
        _crash("d", "41.88", "-88.05"),           # DuPage: fuera de la envolvente estricta
        _crash("e", "41.90", "-87.40"),           # Lago Michigan
    ]).astype("string")
    clean, quarantine, stats = clean_crashes(df)
    assert list(clean["crash_record_id"]) == ["a"]
    assert stats["duplicates_removed"] == 1
    assert dict(zip(quarantine["crash_record_id"], quarantine["reason"])) == {
        "b": "zero_coordinates", "c": "missing_coordinates",
        "d": "outside_chicago_bbox", "e": "outside_chicago_bbox"}


def test_people_age_and_sex_sanitized():
    df = pd.DataFrame([
        {"crash_record_id": "a", "person_id": "p1", "age": "-3", "sex": "m"},
        {"crash_record_id": "a", "person_id": "p2", "age": "34", "sex": "U"},
    ]).astype("string")
    out, _ = clean_people(df)
    assert out["age"].isna().iloc[0] and out["age"].iloc[1] == 34
    assert out["sex"].iloc[0] == "M" and pd.isna(out["sex"].iloc[1])


def test_incremental_where_uses_updated_at_watermark():
    w = build_where(DATASETS["crashes"], since="2023-01-01",
                    watermark={"max_updated_at": "2026-10-01T00:00:00.000", "max_value": "2026-09-30T23:00:00"})
    # Nuevos y modificados (choques reportados tarde o corregidos), sin traer histórico anterior a since
    assert w == "crash_date >= '2023-01-01T00:00:00' AND :updated_at > '2026-10-01T00:00:00.000'"


def test_legacy_watermark_redownloads_lookback_window():
    w = build_where(DATASETS["crashes"], since=None, watermark="2026-10-01T00:00:00.000", lookback_days=90)
    assert w == "crash_date >= '2026-07-03T00:00:00'"


def test_full_load_where_and_select_include_updated_at():
    assert build_where(DATASETS["crashes"], since="2023-01-01", watermark=None) == "crash_date >= '2023-01-01T00:00:00'"
    assert build_where(DATASETS["aadt"], since=None, watermark=None) is None


def test_dedup_keeps_latest_download_and_speed_zero_is_missing():
    old = _crash("a", "41.88", "-87.63")
    new = {**_crash("a", "41.88", "-87.63"), "injuries_fatal": "1", "posted_speed_limit": "0"}
    df = pd.DataFrame([new, old]).astype("string")
    # La versión corregida llega en una descarga posterior (part 10 > part 9, no lexicográfico)
    df["_part"] = pd.Series(["10", "9"], dtype="string")
    df["_updated_at"] = pd.Series(["2026-10-05T00:00:00.000", "2026-01-01T00:00:00.000"], dtype="string")
    clean, _, stats = clean_crashes(df)
    assert len(clean) == 1 and stats["duplicates_removed"] == 1
    row = clean.iloc[0]
    assert row["injuries_fatal"] == 1
    assert pd.isna(row["posted_speed_limit"])
    assert not {"_part", "_updated_at"} & set(clean.columns)
