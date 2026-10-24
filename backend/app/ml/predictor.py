"""Wrapper de inferencia: modelo serializado o estimador heurístico de respaldo."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

import joblib
import numpy as np
import pandas as pd

from app.core.severity import SEVERITY_LABELS
from app.ml.feature_engineering import CATEGORICAL_FEATURES, FEATURES, MECHANISM_FEATURES, build_features

logger = logging.getLogger("ml.predictor")

# Nombre legible de cada variable base (para la explicación de factores)
FEATURE_LABELS = {
    "hour_sin": "hora del día", "hour_cos": "hora del día", "crash_hour": "hora del día",
    "day_of_week": "día de la semana", "crash_month": "mes", "is_weekend": "fin de semana",
    "is_rush_hour": "hora pico", "is_night": "horario nocturno", "posted_speed_limit": "límite de velocidad",
    "aadt_log": "volumen de tráfico (AADT)", "aadt_imputed": "sin aforo cercano",
    "active_workzone": "obra vial activa (250 m)", "intersection_related": "intersección",
    "grid_density": "densidad histórica de siniestros", "latitude": "ubicación", "longitude": "ubicación",
    "weather_group": "clima", "lighting_group": "iluminación", "surface_group": "superficie de calzada",
    "trafficway_type": "tipo de vía", "traffic_control_device": "dispositivo de control",
    "first_crash_type": "tipo de colisión", "prim_contributory_cause": "causa contributiva", "num_units": "unidades involucradas", "hit_and_run": "fuga",
    "has_motorcycle": "motocicleta", "has_pedestrian": "peatón", "has_cyclist": "ciclista",
}


def _base_feature(encoded_name: str) -> str:
    name = encoded_name.split("__", 1)[-1]
    for cat in CATEGORICAL_FEATURES:
        if name.startswith(cat + "_"):
            return cat
    return name


@dataclass
class RiskPredictor:
    model_path: str
    pipeline: object | None = None
    meta: dict = field(default_factory=dict)
    load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self.pipeline is not None

    def load(self) -> bool:
        if not os.path.exists(self.model_path):
            logger.warning("Modelo no encontrado en %s: se usa el estimador heurístico de respaldo", self.model_path)
            return False
        try:
            t0 = time.perf_counter()
            artifact = joblib.load(self.model_path)
            if isinstance(artifact, dict):
                self.pipeline, self.meta = artifact["pipeline"], artifact.get("meta", {})
            else:
                self.pipeline, self.meta = artifact, {}
            self.meta["load_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            logger.info("Modelo %s cargado en %.1f ms", self.meta.get("algorithm"), self.meta["load_ms"])
            return True
        except Exception as exc:  # artefacto corrupto o incompatible
            self.load_error = str(exc)
            self.pipeline = None
            logger.exception("No se pudo cargar el modelo; se usa la heurística de respaldo")
            return False

    # ------------------------------------------------------------------
    def predict(self, raw: dict) -> dict:
        X = build_features(pd.DataFrame([raw]))
        profiles = self.meta.get("mechanism_profiles")
        if self.loaded and profiles and not raw.get("first_crash_type"):
            # Riesgo del tramo = E[P(severidad | condiciones, mecanismo)] sobre los
            # mecanismos de siniestro históricamente más frecuentes
            prof = pd.DataFrame(profiles)
            Xm = pd.concat([X] * len(prof), ignore_index=True)
            for col in MECHANISM_FEATURES:
                Xm[col] = prof[col].to_numpy()
            proba = np.average(self.pipeline.predict_proba(Xm[FEATURES]), axis=0, weights=prof["weight"])
            factors = self._explain(Xm.iloc[[int(prof["weight"].idxmax())]])
        elif self.loaded:
            proba = self.pipeline.predict_proba(X[FEATURES])[0]
            factors = self._explain(X)
        else:
            proba, factors = self._heuristic(X.iloc[0])
        cls = int(np.argmax(proba))
        threshold = float(self.meta.get("critical_threshold_f1", 0.5))
        return {
            "risk_class": cls,
            "risk_level": SEVERITY_LABELS[cls],
            "probabilities": {SEVERITY_LABELS[i]: round(float(p), 4) for i, p in enumerate(proba)},
            "critical_score": round(float(proba[2]), 4),
            "critical_alert": bool(proba[2] >= threshold),
            "top_factors": factors,
        }

    def _explain(self, X: pd.DataFrame, top: int = 5) -> list[dict]:
        """Contribuciones SHAP nativas de XGBoost (pred_contribs) hacia la clase Crítica."""
        model = self.pipeline.named_steps["model"]
        prep = self.pipeline.named_steps["prep"]
        names = prep.get_feature_names_out()
        Xt = prep.transform(X[FEATURES])
        if hasattr(model, "get_booster"):
            import xgboost as xgb
            contribs = model.get_booster().predict(xgb.DMatrix(Xt, feature_names=list(names)), pred_contribs=True)
            crit = np.asarray(contribs)[0, 2, :-1] if np.ndim(contribs) == 3 else np.asarray(contribs)[0, :-1]
        else:
            # Random Forest: importancia global ponderada por la activación local
            crit = model.feature_importances_ * np.abs(Xt[0])
        agg: dict[str, float] = {}
        for n, c in zip(names, crit):
            label = FEATURE_LABELS.get(_base_feature(n), _base_feature(n))
            agg[label] = agg.get(label, 0.0) + float(c)
        ranked = sorted(agg.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top]
        return [{"feature": k, "contribution": round(v, 4), "direction": "aumenta" if v >= 0 else "reduce"}
                for k, v in ranked]

    @staticmethod
    def _heuristic(x: pd.Series) -> tuple[np.ndarray, list[dict]]:
        """Puntuación ponderada de respaldo (antes de entrenar el modelo)."""
        weights = {
            "límite de velocidad": 0.02 * max((x["posted_speed_limit"] or 30) - 25, 0),
            "horario nocturno": 0.25 * x["is_night"],
            "iluminación": 0.3 if x["lighting_group"] == "DARK" else 0.0,
            "clima": 0.15 if x["weather_group"] in ("RAIN", "SNOW", "FOG") else 0.0,
            "obra vial activa (250 m)": 0.2 * x["active_workzone"],
        }
        score = sum(weights.values())
        p_crit = float(np.clip(0.02 + 0.05 * score, 0.0, 0.5))
        p_mod = float(np.clip(0.55 + 0.1 * score, 0.0, 1.0 - p_crit))
        proba = np.array([1.0 - p_mod - p_crit, p_mod, p_crit])
        factors = [{"feature": k, "contribution": round(v, 4), "direction": "aumenta"}
                   for k, v in sorted(weights.items(), key=lambda kv: kv[1], reverse=True) if v > 0]
        return proba, factors
