"""Pruebas de la validación sin fugas de los modelos (no requieren PostGIS)."""
from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.ml import segment_model as sm
from app.ml.evaluation import (bootstrap_capture, calibration, decide, paired_diff, recall_threshold,
                               temporal_masks, top_share_capture)
from app.ml.feature_engineering import FEATURES, add_grid_density, build_features, years_span


def test_temporal_masks_are_disjoint_and_ordered():
    dates = pd.Series(pd.date_range("2023-01-01", "2026-10-23", freq="D"))
    tr, va, te, cut = temporal_masks(dates, test_months=12, val_months=6)
    assert not (tr & va).any() and not (va & te).any() and (tr | va | te).all()
    assert dates[tr].max() < dates[va].min() and dates[va].max() < dates[te].min()
    assert cut["test"].startswith("2025-10-24")


def test_grid_density_ignores_future_rows():
    df = pd.DataFrame({
        "crash_date": pd.to_datetime(["2023-01-01", "2024-01-01", "2025-06-01", "2025-07-01"]),
        "grid_x": [1, 1, 1, 2], "grid_y": [1, 1, 1, 2],
    })
    history = df["crash_date"] < "2025-01-01"
    out = add_grid_density(df, history=history)
    years = years_span(df.loc[history, "crash_date"])
    assert out["grid_density"].iloc[0] == pytest.approx(2 / years)   # sólo cuenta 2023-2024
    assert out["grid_density"].iloc[3] == 0.0                          # celda sin historia previa
    full = add_grid_density(df)
    assert full["grid_density"].iloc[0] == pytest.approx(3 / years_span(df["crash_date"]))


def test_intersection_flag_null_is_zero_not_median():
    X = build_features(pd.DataFrame([
        {"crash_date": "2025-03-04 08:30", "intersection_related_i": True},
        {"crash_date": "2025-03-04 08:30", "intersection_related_i": None},
    ]))
    assert list(X.columns) == FEATURES
    assert X["intersection_related"].tolist() == [1.0, 0.0]


def test_recall_threshold_and_decision_rule():
    rng = np.random.default_rng(0)
    y = rng.random(5000) < 0.05
    p = np.clip(0.05 + 0.3 * y + rng.normal(0, 0.1, 5000), 0, 1)
    thr = recall_threshold(y, p, 0.6)
    assert ((p >= thr) & y).sum() / y.sum() >= 0.6
    proba = np.array([[0.6, 0.3, 0.1], [0.2, 0.7, 0.1], [0.5, 0.45, 0.05]])
    assert decide(proba, 2, 0.08).tolist() == [2, 2, 0]


def test_calibration_of_calibrated_scores_is_small():
    rng = np.random.default_rng(1)
    p = rng.uniform(0, 0.2, 50_000)
    y = rng.random(50_000) < p
    cal = calibration(y, p)
    assert cal["ece"] < 0.01 and abs(cal["mean_predicted"] - cal["observed_rate"]) < 0.01


def test_bootstrap_capture_and_paired_diff():
    rng = np.random.default_rng(2)
    events = rng.poisson(0.2, 2000).astype(float)
    good = events + rng.normal(0, 0.5, 2000)
    rand = rng.random(2000)
    assert top_share_capture(good, events) > top_share_capture(rand, events)
    boot = bootstrap_capture({"good": good, "rand": rand}, events, reps=200)
    lo, hi = boot["good"]["ci95"]
    assert lo <= boot["good"]["capture"] <= hi
    assert paired_diff(boot, "good", "rand")["significant"]


def test_segment_windows_are_contiguous_and_need_36_months():
    w = sm.make_windows(date(2026, 10, 24), first_date=date(2023, 1, 1))
    (h0, h1), (l0, l1) = w["train"]
    (th0, th1), (tl0, tl1) = w["test"]
    assert h1 == l0 == th0 and l1 == th1 == tl0 and tl1 == date(2026, 10, 24)
    assert w["forecast"] == (tl0, tl1)
    with pytest.raises(ValueError):
        sm.make_windows(date(2025, 6, 1), first_date=date(2023, 1, 1))


def test_segment_sql_excludes_crashes_without_block_number():
    assert "street_no ~ '[0-9]'" in sm.FEATURES_SQL and "street_no ~ '[0-9]'" in sm.LABELS_SQL
    # La cuadra pedida se filtra dentro del CTE (no tras agregar todo el año)
    cte = sm.SEGMENT_FEATURES_SQL.split("cell AS")[0]
    assert "%(seg)s" in cte and "%(seg)s" not in sm.FEATURES_SQL


def test_train_end_to_end_on_synthetic_data(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.ml import train

    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "DUCKDB_PATH", str(tmp_path / "gold.duckdb"))
    monkeypatch.setattr(train, "PARAM_GRIDS", {"xgboost": {"max_depth": [3], "n_estimators": [30]}})
    rng = np.random.default_rng(0)
    n = 4000
    raw = pd.DataFrame({
        "crash_date": pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, 1300, n), unit="D"),
        "grid_x": rng.integers(0, 20, n), "grid_y": rng.integers(0, 20, n),
        "lighting_condition": rng.choice(["DAYLIGHT", "DARKNESS"], n),
        "first_crash_type": rng.choice(["PEDESTRIAN", "REAR END", "ANGLE"], n),
        "num_units": rng.choice([1, 2], n), "latitude": 41.85, "longitude": -87.65,
    })
    raw["has_pedestrian"] = raw["first_crash_type"] == "PEDESTRIAN"
    logit = -3.0 + 2.0 * raw["has_pedestrian"] + 0.5 * (raw["lighting_condition"] == "DARKNESS")
    crit = rng.random(n) < 1 / (1 + np.exp(-logit))
    raw = add_grid_density(raw)
    feats = build_features(raw)
    feats["target"] = np.where(crit, 2, np.where(rng.random(n) < 0.6, 1, 0))
    for c in ("crash_date", "grid_x", "grid_y"):
        feats[c] = raw[c]
    path = tmp_path / "features.parquet"
    feats.to_parquet(path)

    report = train.train(str(path), ["xgboost"], 2000, str(tmp_path / "models" / "m.joblib"))
    m = report["models"]["xgboost"]
    assert report["selection_metric"] == "val_auc_macro"
    assert set(report["windows"]) == {"train", "val", "test"}
    assert m["test_decision"]["threshold"] == pytest.approx(
        __import__("joblib").load(tmp_path / "models" / "m.joblib")["meta"]["critical_threshold"])
    assert {"brier", "ece", "reliability"} <= set(m["calibration_critical"])
    assert "auc_roc_ovr_macro" in report["ablation_pre_crash_only"]
    assert (tmp_path / "processed" / "gold_grid_ml.parquet").exists()
