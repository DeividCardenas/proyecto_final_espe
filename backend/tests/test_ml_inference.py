import os
import time

import joblib
import pandas as pd
import pytest

from app.core.config import settings
from app.ml.feature_engineering import FEATURES, build_features

PAYLOAD = {
    "coordinates": [-87.6298, 41.8781],
    "posted_speed_limit": 30,
    "weather_condition": "RAIN",
    "lighting_condition": "DARKNESS",
    "active_workzone": True,
}

model_missing = pytest.mark.skipif(not os.path.exists(settings.MODEL_PATH), reason="modelo no entrenado")


def test_build_features_columns_and_groups():
    df = build_features(pd.DataFrame([{
        "crash_date": "2025-03-04 08:30", "weather_condition": "FREEZING RAIN/DRIZZLE",
        "lighting_condition": "DARKNESS, LIGHTED ROAD", "posted_speed_limit": 30,
    }]))
    assert list(df.columns) == FEATURES
    row = df.iloc[0]
    assert row["weather_group"] == "RAIN" and row["lighting_group"] == "DARK_LIGHTED"
    assert row["is_rush_hour"] == 1 and row["is_weekend"] == 0


@model_missing
def test_artifact_size_and_load_time():
    assert os.path.getsize(settings.MODEL_PATH) < 100 * 1024 * 1024
    t0 = time.perf_counter()
    art = joblib.load(settings.MODEL_PATH)
    assert (time.perf_counter() - t0) < 2.0
    assert set(art["meta"]["features"]) == set(FEATURES)


@model_missing
def test_unit_inference_under_50ms():
    art = joblib.load(settings.MODEL_PATH)
    X = build_features(pd.DataFrame([{"crash_date": "2025-01-10 22:00", "posted_speed_limit": 35}]))
    art["pipeline"].predict_proba(X)  # calentamiento
    t0 = time.perf_counter()
    proba = art["pipeline"].predict_proba(X)
    assert (time.perf_counter() - t0) < 0.05
    assert proba.shape == (1, 3) and abs(proba.sum() - 1) < 1e-5


def test_predict_endpoint_contract(client):
    r = client.post("/api/v1/predict/segment-risk", json=PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["risk_level"] in ("Bajo", "Moderado", "Crítico")
    assert abs(sum(body["probabilities"].values()) - 1) < 1e-3
    assert body["top_factors"]
    assert body["inference_ms"] < 500


def test_predict_rejects_outside_chicago(client):
    r = client.post("/api/v1/predict/segment-risk", json={**PAYLOAD, "coordinates": [-74.006, 40.7128]})
    assert r.status_code == 422


def test_predict_rejects_bad_enum(client):
    r = client.post("/api/v1/predict/segment-risk", json={**PAYLOAD, "weather_condition": "TORNADO"})
    assert r.status_code == 422
