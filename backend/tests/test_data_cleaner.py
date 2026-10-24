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


def test_incremental_where_uses_watermark():
    w = build_where(DATASETS["crashes"], since="2023-01-01", watermark="2026-10-01T00:00:00.000")
    assert w == "crash_date > '2026-10-01T00:00:00.000'"
