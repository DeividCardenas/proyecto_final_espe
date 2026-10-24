"""Modelo de riesgo por tramo vial (unidad de predicción = cuadra / "hundred block").

Responde al OE3 ("clasificar segmentos viales según su nivel de riesgo") y a la
pregunta de decisión: con el historial de un año de cada tramo se **anticipa** su
nivel de riesgo del año siguiente, para priorizar intervenciones preventivas.

* Unidad: cuadra de Chicago = centena del número + dirección + calle
  (p. ej. ``1500 N ASHLAND AVE``), con geometría en el centroide de sus siniestros.
* Variables (ventana de historia de 12 meses): frecuencia y severidad de
  siniestros, usuarios vulnerables, horario nocturno, velocidad, tipo de vía,
  intersecciones, AADT, obras, clima y densidad del entorno (celda de 500 m).
* Etiqueta (ventana objetivo de los 12 meses siguientes):
    2 Alto:  al menos un siniestro con fallecidos o lesiones incapacitantes.
    1 Medio: sin siniestros graves, pero con al menos un siniestro con lesionados.
    0 Bajo:  sin siniestros con lesionados (o sin siniestros).
* Modelos: Regresión Logística (línea base), Random Forest y XGBoost.
* Validación:
    - Temporal: entrena con historia 2023 -> etiqueta 2024 y evalúa con
      historia 2024 -> etiqueta 2025 (nunca ve el futuro).
    - Espacial: GroupKFold de 5 pliegues por bloques de ~2 km sobre el conjunto
      de entrenamiento (tramos vecinos no se reparten entre train y validación).
* Priorización: % de los siniestros graves del año siguiente que ocurren en el
  10% de tramos con mayor probabilidad de riesgo Alto (captura / lift).

Uso:
    python -m app.ml.segment_model
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.database import raw_connection
from app.core.severity import GRID_SIZE_FT

logger = logging.getLogger("ml.segments")

SEED = 42
HIGH = 2
SEGMENT_LABELS = {0: "Bajo", 1: "Medio", 2: "Alto"}
SEGMENT_MODEL_PATH = str(Path(settings.MODEL_PATH).with_name("chicago_segment_risk.joblib"))

# Identificador de cuadra (centena del número de calle) reutilizado en todas las consultas
SEGMENT_ID_SQL = (
    "concat_ws(' ', (floor(nullif(regexp_replace(street_no, '\\D', '', 'g'), '')::bigint / 100) * 100)::text, "
    "street_direction, street_name)"
)

FEATURES_SQL = f"""
WITH c AS (
    SELECT {SEGMENT_ID_SQL} AS segment_id, *
    FROM silver_crashes
    WHERE street_name IS NOT NULL AND crash_date >= %(start)s AND crash_date < %(end)s
),
cell AS (
    SELECT floor(ST_X(geom_3435) / {GRID_SIZE_FT})::int AS gx, floor(ST_Y(geom_3435) / {GRID_SIZE_FT})::int AS gy,
           count(*) AS cell_crashes
    FROM silver_crashes
    WHERE crash_date >= %(start)s AND crash_date < %(end)s
    GROUP BY 1, 2
),
seg AS (
    SELECT segment_id,
           count(*) AS crashes,
           count(*) FILTER (WHERE injuries_total > 0) AS injury_crashes,
           count(*) FILTER (WHERE severity = 2) AS severe_crashes,
           coalesce(sum(injuries_total), 0) AS injuries,
           coalesce(sum(injuries_fatal), 0) AS fatalities,
           count(*) FILTER (WHERE first_crash_type = 'PEDESTRIAN') AS ped_crashes,
           count(*) FILTER (WHERE first_crash_type = 'PEDALCYCLIST') AS bike_crashes,
           avg((crash_hour >= 21 OR crash_hour <= 5)::int) AS night_share,
           avg(coalesce(intersection_related_i, false)::int) AS intersection_share,
           avg(coalesce(hit_and_run_i, false)::int) AS hit_and_run_share,
           avg((weather_condition IN ('RAIN', 'SNOW', 'FREEZING RAIN/DRIZZLE', 'SLEET/HAIL'))::int) AS bad_weather_share,
           avg(active_workzone::int) AS workzone_share,
           avg(posted_speed_limit) AS mean_speed,
           max(posted_speed_limit) AS max_speed,
           avg(aadt_volume) AS mean_aadt,
           avg(aadt_imputed::int) AS aadt_imputed_share,
           mode() WITHIN GROUP (ORDER BY trafficway_type) AS trafficway_type,
           mode() WITHIN GROUP (ORDER BY traffic_control_device) AS traffic_control_device,
           avg(lane_cnt) AS mean_lanes,
           ST_Y(ST_Centroid(ST_Collect(geom))) AS lat,
           ST_X(ST_Centroid(ST_Collect(geom))) AS lon,
           floor(ST_X(ST_Centroid(ST_Collect(geom_3435))) / {GRID_SIZE_FT})::int AS gx,
           floor(ST_Y(ST_Centroid(ST_Collect(geom_3435))) / {GRID_SIZE_FT})::int AS gy
    FROM c GROUP BY segment_id
)
SELECT seg.*, coalesce(cell.cell_crashes, 0) AS cell_crashes
FROM seg LEFT JOIN cell USING (gx, gy)
"""

LABELS_SQL = f"""
SELECT {SEGMENT_ID_SQL} AS segment_id,
       count(*) FILTER (WHERE severity = 2) AS future_severe,
       count(*) FILTER (WHERE injuries_total > 0) AS future_injury,
       count(*) AS future_crashes
FROM silver_crashes
WHERE street_name IS NOT NULL AND crash_date >= %(start)s AND crash_date < %(end)s
GROUP BY 1
"""

NUMERIC = [
    "crashes_log", "injury_rate", "severe_crashes", "fatalities", "ped_crashes", "bike_crashes", "night_share",
    "intersection_share", "hit_and_run_share", "bad_weather_share", "workzone_share", "mean_speed", "max_speed",
    "aadt_log", "aadt_imputed_share", "mean_lanes", "cell_crashes_log", "lat", "lon",
]
CATEGORICAL = ["trafficway_type", "traffic_control_device"]
FEATURES = NUMERIC + CATEGORICAL


def _query(sql: str, params: dict) -> pd.DataFrame:
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def build_segment_features(start: date, end: date) -> pd.DataFrame:
    df = _query(FEATURES_SQL, {"start": start, "end": end})
    for col in df.columns:
        if col not in ("segment_id", "trafficway_type", "traffic_control_device"):
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    df["crashes_log"] = np.log1p(df["crashes"])
    df["injury_rate"] = df["injury_crashes"] / df["crashes"]
    df["aadt_log"] = np.log1p(df["mean_aadt"])
    df["cell_crashes_log"] = np.log1p(df["cell_crashes"])
    for col in CATEGORICAL:
        df[col] = df[col].fillna("UNKNOWN").astype(str)
    return df


def build_dataset(hist: tuple[date, date], target: tuple[date, date]) -> pd.DataFrame:
    X = build_segment_features(*hist)
    y = _query(LABELS_SQL, {"start": target[0], "end": target[1]})
    df = X.merge(y, on="segment_id", how="left")
    for col in ("future_severe", "future_injury", "future_crashes"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["target"] = np.select([df["future_severe"] > 0, df["future_injury"] > 0], [2, 1], 0).astype(int)
    return df


def preprocessor(scale: bool) -> ColumnTransformer:
    steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scale", StandardScaler()))
    cat = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                    ("onehot", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=50,
                                             sparse_output=False))])
    return ColumnTransformer([("num", Pipeline(steps), NUMERIC), ("cat", cat, CATEGORICAL)])


def make_pipeline(name: str) -> Pipeline:
    if name == "logistic_regression":
        model = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0)
        return Pipeline([("prep", preprocessor(scale=True)), ("model", model)])
    if name == "random_forest":
        model = RandomForestClassifier(n_estimators=400, max_depth=12, min_samples_leaf=10,
                                       class_weight="balanced_subsample", n_jobs=os.cpu_count(), random_state=SEED)
        return Pipeline([("prep", preprocessor(scale=False)), ("model", model)])
    if name == "xgboost":
        model = XGBClassifier(objective="multi:softprob", num_class=3, tree_method="hist", n_estimators=400,
                              learning_rate=0.03, max_depth=4, subsample=0.8, colsample_bytree=0.8,
                              min_child_weight=5, n_jobs=os.cpu_count(), random_state=SEED, eval_metric="mlogloss")
        return Pipeline([("prep", preprocessor(scale=False)), ("model", model)])
    raise ValueError(name)


def fit(pipe: Pipeline, X: pd.DataFrame, y: pd.Series) -> Pipeline:
    if isinstance(pipe.named_steps["model"], XGBClassifier):
        pipe.fit(X, y, model__sample_weight=compute_sample_weight("balanced", y))
    else:
        pipe.fit(X, y)
    return pipe


def evaluate(y: np.ndarray, proba: np.ndarray, future_severe: np.ndarray, top_share: float = 0.10) -> dict:
    pred = proba.argmax(axis=1)
    n_top = max(1, int(len(y) * top_share))
    order = np.argsort(-proba[:, HIGH])
    captured = future_severe[order[:n_top]].sum()
    total_severe = future_severe.sum()
    capture = float(captured / total_severe) if total_severe else 0.0
    return {
        "auc_roc_ovr_macro": float(roc_auc_score(y, proba, multi_class="ovr", average="macro")),
        "auc_roc_high_vs_rest": float(roc_auc_score(y == HIGH, proba[:, HIGH])),
        "recall_high": float(recall_score(y == HIGH, pred == HIGH, zero_division=0)),
        "precision_high": float(precision_score(y == HIGH, pred == HIGH, zero_division=0)),
        "base_rate_high": float((y == HIGH).mean()),
        "top10_precision_high": float((y[order[:n_top]] == HIGH).mean()),
        "top10_capture_severe": capture,
        "top10_lift": capture / top_share,
    }


def spatial_cv(name: str, X: pd.DataFrame, y: pd.Series, groups: pd.Series) -> dict:
    folds = []
    for tr, va in GroupKFold(n_splits=5).split(X, y, groups):
        pipe = fit(make_pipeline(name), X.iloc[tr], y.iloc[tr])
        p = pipe.predict_proba(X.iloc[va])
        folds.append(float(roc_auc_score(y.iloc[va], p, multi_class="ovr", average="macro")))
    a = np.array(folds)
    return {"auc_folds": folds, "auc_mean": float(a.mean()), "auc_std": float(a.std()),
            "auc_cv_variation": float(a.std() / a.mean())}


def importance(pipe: Pipeline, top: int = 15) -> list[dict]:
    names = pipe.named_steps["prep"].get_feature_names_out()
    model = pipe.named_steps["model"]
    imp = np.abs(model.coef_).mean(axis=0) if hasattr(model, "coef_") else model.feature_importances_
    order = np.argsort(imp)[::-1][:top]
    return [{"feature": str(names[i]).split("__", 1)[-1], "importance": float(imp[i])} for i in order]


def run(model_path: str = SEGMENT_MODEL_PATH) -> dict:
    t0 = time.perf_counter()
    train = build_dataset((date(2023, 1, 1), date(2024, 1, 1)), (date(2024, 1, 1), date(2025, 1, 1)))
    test = build_dataset((date(2024, 1, 1), date(2025, 1, 1)), (date(2025, 1, 1), date(2026, 1, 1)))
    logger.info("Tramos train=%d test=%d | clases train %s", len(train), len(test),
                train["target"].value_counts(normalize=True).round(3).to_dict())

    # Bloques espaciales de ~2 km (4 x 4 celdas de 500 m) para la CV espacial
    groups = (train["gx"] // 4).astype(int).astype(str) + "_" + (train["gy"] // 4).astype(int).astype(str)
    report: dict = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "unit": "cuadra (centena de número + dirección + calle)",
        "windows": {"train": "historia 2023 -> riesgo 2024", "test": "historia 2024 -> riesgo 2025"},
        "n_train": int(len(train)), "n_test": int(len(test)),
        "class_distribution_train": {SEGMENT_LABELS[k]: float(v) for k, v in
                                     train["target"].value_counts(normalize=True).items()},
        "class_distribution_test": {SEGMENT_LABELS[k]: float(v) for k, v in
                                    test["target"].value_counts(normalize=True).items()},
        "models": {},
    }
    fitted = {}
    for name in ("logistic_regression", "random_forest", "xgboost"):
        cv = spatial_cv(name, train[FEATURES], train["target"], groups)
        pipe = fit(make_pipeline(name), train[FEATURES], train["target"])
        proba = pipe.predict_proba(test[FEATURES])
        m = evaluate(test["target"].to_numpy(), proba, test["future_severe"].to_numpy())
        report["models"][name] = {
            "spatial_cv": cv,
            "temporal_test": m,
            "confusion_matrix": confusion_matrix(test["target"], proba.argmax(axis=1)).tolist(),
            "feature_importance": importance(pipe),
        }
        fitted[name] = pipe
        logger.info("[%s] CV espacial AUC %.3f ± %.3f | test temporal %s", name, cv["auc_mean"], cv["auc_std"],
                    {k: round(v, 3) for k, v in m.items()})

    # Criterio de selección alineado con la pregunta de decisión: el modelo que más
    # siniestros graves futuros concentra en el 10% de tramos priorizados.
    winner = max(report["models"], key=lambda k: report["models"][k]["temporal_test"]["top10_capture_severe"])
    report["selection_metric"] = "top10_capture_severe"
    report["winner"] = winner
    report["baseline_gain_auc"] = (report["models"][winner]["temporal_test"]["auc_roc_ovr_macro"]
                                   - report["models"]["logistic_regression"]["temporal_test"]["auc_roc_ovr_macro"])

    # Modelo de producción: reentrena el ganador con la ventana más reciente con
    # etiqueta completa (historia 2024 -> riesgo 2025) y anticipa los próximos
    # 12 meses a partir de la historia de los últimos 12 meses disponibles.
    final = fit(make_pipeline(winner), test[FEATURES], test["target"])
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT max(crash_date)::date FROM silver_crashes")
        last = cur.fetchone()[0]
    hist_end = last + pd.Timedelta(days=1)
    hist_start = (pd.Timestamp(hist_end) - pd.DateOffset(years=1)).date()
    current = build_segment_features(hist_start, hist_end)
    p = final.predict_proba(current[FEATURES])
    current["p_bajo"], current["p_medio"], current["p_alto"] = p[:, 0], p[:, 1], p[:, 2]
    current["risk_class"] = p.argmax(axis=1)
    current["priority_rank"] = current["p_alto"].rank(ascending=False, method="first").astype(int)
    current["priority_pct"] = current["priority_rank"] / len(current)
    out_cols = ["segment_id", "lat", "lon", "crashes", "injury_crashes", "severe_crashes", "fatalities",
                "ped_crashes", "bike_crashes", "mean_speed", "mean_aadt", "workzone_share", "p_bajo", "p_medio",
                "p_alto", "risk_class", "priority_rank", "priority_pct"]
    scored = current[out_cols].sort_values("priority_rank")
    scored.to_parquet(settings.processed_dir / "gold_segment_risk.parquet", index=False)
    report["forecast"] = {
        "history_window": f"{hist_start} -> {hist_end}",
        "segments_scored": int(len(scored)),
        "high_risk_segments": int((scored["risk_class"] == HIGH).sum()),
        "top10": scored.head(10)[["segment_id", "p_alto", "severe_crashes", "crashes"]].round(3).to_dict(orient="records"),
    }

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": final, "meta": {"algorithm": winner, "features": FEATURES, "classes": SEGMENT_LABELS,
                                             "trained_at": report["trained_at"]}}, model_path, compress=3)
    try:
        from app.services.olap.duckdb_engine import attach_table
        attach_table("gold_segment_risk", scored)
    except Exception as exc:  # DuckDB bloqueado o inexistente: no es fatal
        logger.warning("No se pudo adjuntar gold_segment_risk a DuckDB: %s", exc)

    report["elapsed_s"] = round(time.perf_counter() - t0, 1)
    text = json.dumps(report, indent=2, default=str)
    (settings.processed_dir / "segment_model_report.json").write_text(text, encoding="utf-8")
    Path(model_path).with_name("segment_model_report.json").write_text(text, encoding="utf-8")
    logger.info("Ganador: %s | ganancia AUC sobre la línea base: %+.3f", winner, report["baseline_gain_auc"])
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Modelo de riesgo por tramo vial")
    parser.add_argument("--model-path", default=SEGMENT_MODEL_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    r = run(args.model_path)
    print(json.dumps({k: r[k] for k in ("winner", "baseline_gain_auc", "class_distribution_test")}, indent=2))
    for name, m in r["models"].items():
        print(name, json.dumps({"cv": round(m["spatial_cv"]["auc_mean"], 3),
                                **{k: round(v, 3) for k, v in m["temporal_test"].items()}}))


if __name__ == "__main__":
    main()
