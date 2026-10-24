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


segment_missing = pytest.mark.skipif(
    not os.path.exists(os.path.join(os.path.dirname(settings.MODEL_PATH), "segment_model_report.json")),
    reason="modelo por tramo no entrenado")


@segment_missing
def test_segment_model_beats_random_and_validates_out_of_time(client):
    m = client.get("/api/v1/risk/segment-model-metrics").json()
    assert set(m["comparison"]) == {"logistic_regression", "random_forest", "xgboost"}
    best = m["comparison"][m["winner"]]
    assert best["auc_roc_ovr_macro"] >= 0.70           # validación temporal (año siguiente)
    assert best["spatial_cv_variation"] < 0.05         # estabilidad entre bloques espaciales
    assert best["top10_lift"] > 2                      # el 10% priorizado concentra siniestros graves


@segment_missing
def test_segments_geojson_sorted_by_priority(client):
    fc = client.get("/api/v1/risk/segments", params={"limit": 50, "min_class": 2}).json()
    ranks = [f["properties"]["priority_rank"] for f in fc["features"]]
    assert ranks == sorted(ranks) and all(f["properties"]["risk_class"] == 2 for f in fc["features"])
