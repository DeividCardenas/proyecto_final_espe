"""Explicación local de la predicción del modelo por tramo vial.

El modelo de producción es una regresión logística multinomial, de modo que la
predicción de una cuadra se descompone de forma exacta en el espacio log-odds:

    log(P(Alto) / P(Bajo)) = (b_Alto - b_Bajo) + sum_j (w_Alto,j - w_Bajo,j) * x_j

* Variables numéricas: ``x_j`` está estandarizada (0 = media de las cuadras de
  entrenamiento), así que cada término es el aporte de esa variable frente a una
  cuadra promedio.
* Variables categóricas (tipo de vía, control de tráfico): el aporte de la
  categoría activa se centra restando la media de los pesos de sus categorías
  (aproximación, documentada en la respuesta).

Las variables se recalculan desde PostGIS con la misma ventana de historia que
usó la predicción publicada (``forecast.history_window`` del informe), y se
devuelve P(Alto) recalculada para comprobar que coincide con la publicada.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from app.core.config import settings
from app.ml.segment_model import CATEGORICAL, FEATURES, NUMERIC, SEGMENT_MODEL_PATH, build_segment_features

LOW, HIGH = 0, 2

FEATURE_LABELS = {
    "crashes_log": "Siniestros en 12 meses",
    "injury_rate": "Proporción con lesionados",
    "severe_crashes": "Siniestros graves",
    "fatalities": "Fallecidos",
    "ped_crashes": "Atropellos a peatones",
    "bike_crashes": "Siniestros con ciclistas",
    "night_share": "Proporción nocturna (21-5 h)",
    "intersection_share": "Proporción en intersección",
    "hit_and_run_share": "Proporción con fuga",
    "bad_weather_share": "Proporción con mal clima",
    "workzone_share": "Proporción en zona de obra",
    "mean_speed": "Velocidad señalizada media",
    "max_speed": "Velocidad señalizada máxima",
    "aadt_log": "Tráfico diario (AADT)",
    "aadt_imputed_share": "AADT imputado",
    "mean_lanes": "Carriles medios",
    "cell_crashes_log": "Siniestros del entorno (500 m)",
    "location": "Ubicación en la ciudad",
    "trafficway_type": "Tipo de vía",
    "traffic_control_device": "Control de tráfico",
}
UNITS = {
    "crashes_log": "siniestros", "severe_crashes": "siniestros", "fatalities": "personas",
    "ped_crashes": "siniestros", "bike_crashes": "siniestros", "mean_speed": "mph", "max_speed": "mph",
    "aadt_log": "veh/día", "mean_lanes": "carriles", "cell_crashes_log": "siniestros",
}
SHARES = {"injury_rate", "night_share", "intersection_share", "hit_and_run_share", "bad_weather_share",
          "workzone_share", "aadt_imputed_share"}
# Variables modeladas en log1p: se muestran en su escala original
RAW_OF_LOG = {"crashes_log": "crashes", "aadt_log": "mean_aadt", "cell_crashes_log": "cell_crashes"}


@lru_cache(maxsize=1)
def _artifact(mtime: float) -> dict:
    return joblib.load(SEGMENT_MODEL_PATH)


@lru_cache(maxsize=1)
def _report(mtime: float) -> dict:
    return json.loads(Path(SEGMENT_MODEL_PATH).with_name("segment_model_report.json").read_text(encoding="utf-8"))


def _history_window(report: dict) -> tuple[date, date]:
    start, end = (s.strip() for s in report["forecast"]["history_window"].split("->"))
    return date.fromisoformat(start), date.fromisoformat(end)


@lru_cache(maxsize=512)
def explain_segment(segment_id: str, model_mtime: float) -> dict | None:
    art = _artifact(model_mtime)
    pipe = art["pipeline"]
    model = pipe.named_steps["model"]
    if not hasattr(model, "coef_"):
        raise NotImplementedError("La explicación exacta sólo está disponible para la regresión logística")
    report = _report(Path(SEGMENT_MODEL_PATH).with_name("segment_model_report.json").stat().st_mtime)
    start, end = _history_window(report)

    row = build_segment_features(start, end, segment_id=segment_id)
    if row.empty:
        return None
    X = row[FEATURES].head(1)

    prep = pipe.named_steps["prep"]
    Xt = np.asarray(prep.transform(X))[0]
    names = [str(n) for n in prep.get_feature_names_out()]
    delta = model.coef_[HIGH] - model.coef_[LOW]
    intercept = float(model.intercept_[HIGH] - model.intercept_[LOW])
    proba = pipe.predict_proba(X)[0]

    num_pipe = prep.named_transformers_["num"]
    scaler = num_pipe.named_steps["scale"]
    means = dict(zip(NUMERIC, scaler.mean_))

    contrib: dict[str, float] = {}
    for i, n in enumerate(names):
        group, feat = n.split("__", 1)
        if group == "num":
            key = "location" if feat in ("lat", "lon") else feat
            contrib[key] = contrib.get(key, 0.0) + float(delta[i] * Xt[i])
    for cat in CATEGORICAL:
        idx = [i for i, n in enumerate(names) if n.startswith(f"cat__{cat}_")]
        if idx:
            d = delta[idx]
            contrib[cat] = float(d @ Xt[idx] - d.mean())

    values = row.iloc[0]
    factors = []
    for key, c in contrib.items():
        if key == "location":
            value, mean = None, None
        elif key in CATEGORICAL:
            value, mean = str(values[key]), None
        else:
            raw = RAW_OF_LOG.get(key, key)
            value = None if np.isnan(values[raw]) else float(values[raw])
            mean = float(np.expm1(means[key])) if key in RAW_OF_LOG else float(means[key])
        factors.append({
            "feature": key,
            "label": FEATURE_LABELS.get(key, key),
            "contribution": round(c, 4),
            "value": value,
            "city_mean": None if mean is None else round(mean, 4),
            "unit": "proporción" if key in SHARES else UNITS.get(key),
        })
    factors.sort(key=lambda f: -abs(f["contribution"]))

    dist = report["class_distribution_test"]
    return {
        "segment_id": segment_id,
        "history_window": report["forecast"]["history_window"],
        "algorithm": art["meta"]["algorithm"],
        "probabilities": {"Bajo": float(proba[0]), "Medio": float(proba[1]), "Alto": float(proba[2])},
        "base_rate_high": float(dist.get("Alto", 0.0)),
        "log_odds": {"intercept": round(intercept, 4), "total": round(intercept + sum(contrib.values()), 4)},
        "factors": factors,
        "method": ("Aporte de cada variable al log-odds de riesgo Alto frente a Bajo, respecto a una cuadra "
                   "promedio. Exacto para variables numéricas; aproximado (centrado) para las categóricas."),
    }


def model_mtime() -> float:
    return Path(SEGMENT_MODEL_PATH).stat().st_mtime
