"""Modelo de riesgo por tramo vial (unidad de predicción = cuadra / "hundred block").

Responde al OE3 ("clasificar segmentos viales según su nivel de riesgo") y a la
pregunta de decisión: con el historial de un año de cada tramo se **anticipa** su
nivel de riesgo del año siguiente, para priorizar intervenciones preventivas.

* Unidad: cuadra de Chicago = centena del número + dirección + calle
  (p. ej. ``1500 N ASHLAND AVE``), con geometría en el centroide de sus siniestros.
  Se excluyen los siniestros sin número de calle (antes colapsaban en una
  pseudo-cuadra con la calle entera).
* Variables (ventana de historia de 12 meses): frecuencia y severidad de
  siniestros, usuarios vulnerables, horario nocturno, velocidad, tipo de vía,
  intersecciones, AADT, obras, clima y densidad del entorno (celda de 500 m).
* Etiqueta (ventana objetivo de los 12 meses siguientes):
    2 Alto:  al menos un siniestro con fallecidos o lesiones incapacitantes.
    1 Medio: sin siniestros graves, pero con al menos un siniestro con lesionados.
    0 Bajo:  sin siniestros con lesionados (o sin siniestros).
* Ventanas derivadas de los datos (``--anchor-date``, por defecto el día
  siguiente al último siniestro = A):
    - train: historia [A-36m, A-24m) -> etiqueta [A-24m, A-12m)
    - test:  historia [A-24m, A-12m) -> etiqueta [A-12m, A)
    - pronóstico: historia [A-12m, A) -> riesgo de los 12 meses siguientes
* Modelos: Regresión Logística (línea base), Random Forest y XGBoost, sin pesos
  de clase (probabilidades calibradas; se reportan Brier y ECE).
* Líneas base heurísticas: ordenar las cuadras por su historial (siniestros,
  graves o con lesionados del año anterior). Es la comparación que responde a
  "¿el modelo prioriza mejor que la regla obvia?".
* Validación y selección sin mirar el test:
    - GroupKFold espacial (bloques de ~2 km) sobre train: AUC por pliegue y
      predicciones fuera de pliegue, con las que se elige el ganador (captura en
      el top 10 %, regla de un error estándar a favor del modelo más simple) y
      el umbral de la clase Alto.
    - El test temporal se usa una vez, con intervalos bootstrap (IC 95 %) de la
      captura de cada modelo y de cada línea base.
* Regla de decisión: Alto si P(Alto) >= umbral (F1 fuera de pliegue); si no, la
  clase más probable entre Bajo y Medio. Con argmax y pesos balanceados se
  clasificaba como Alto al ~19 % de las cuadras con una tasa real del ~6 %.

Uso:
    python -m app.ml.segment_model
    python -m app.ml.segment_model --anchor-date 2026-10-24
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
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.database import raw_connection
from app.core.severity import GRID_SIZE_FT
from app.ml.evaluation import (bootstrap_capture, calibration, decide, f1_threshold, paired_diff, provenance,
                               top_share_capture)

logger = logging.getLogger("ml.segments")

SEED = 42
HIGH = 2
TOP_SHARE = 0.10
SEGMENT_LABELS = {0: "Bajo", 1: "Medio", 2: "Alto"}
SEGMENT_MODEL_PATH = str(Path(settings.MODEL_PATH).with_name("chicago_segment_risk.joblib"))
# Orden de simplicidad: ante un empate estadístico gana el primero (más interpretable)
MODEL_ORDER = ("logistic_regression", "random_forest", "xgboost")

# Identificador de cuadra (centena del número de calle) reutilizado en todas las consultas
SEGMENT_ID_SQL = (
    "concat_ws(' ', (floor(nullif(regexp_replace(street_no, '\\D', '', 'g'), '')::bigint / 100) * 100)::text, "
    "street_direction, street_name)"
)
# Sin número de calle no hay cuadra: concat_ws ignora el NULL y el id quedaba
# como la calle completa ("N ASHLAND AVE"), mezclando toda su longitud.
HAS_BLOCK_SQL = "street_name IS NOT NULL AND street_no ~ '[0-9]'"


def _features_sql(single_segment: bool) -> str:
    seg_filter = f" AND {SEGMENT_ID_SQL} = %(seg)s" if single_segment else ""
    return f"""
WITH c AS (
    SELECT {SEGMENT_ID_SQL} AS segment_id, *
    FROM silver_crashes
    WHERE {HAS_BLOCK_SQL} AND crash_date >= %(start)s AND crash_date < %(end)s{seg_filter}
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


FEATURES_SQL = _features_sql(single_segment=False)
SEGMENT_FEATURES_SQL = _features_sql(single_segment=True)

LABELS_SQL = f"""
SELECT {SEGMENT_ID_SQL} AS segment_id,
       count(*) FILTER (WHERE severity = 2) AS future_severe,
       count(*) FILTER (WHERE injuries_total > 0) AS future_injury,
       count(*) AS future_crashes
FROM silver_crashes
WHERE {HAS_BLOCK_SQL} AND crash_date >= %(start)s AND crash_date < %(end)s
GROUP BY 1
"""

NUMERIC = [
    "crashes_log", "injury_rate", "severe_crashes", "fatalities", "ped_crashes", "bike_crashes", "night_share",
    "intersection_share", "hit_and_run_share", "bad_weather_share", "workzone_share", "mean_speed", "max_speed",
    "aadt_log", "aadt_imputed_share", "mean_lanes", "cell_crashes_log", "lat", "lon",
]
CATEGORICAL = ["trafficway_type", "traffic_control_device"]
FEATURES = NUMERIC + CATEGORICAL

# Reglas de priorización sin modelo: ordenar por el historial del año anterior.
# El desempate por número total de siniestros evita empates masivos en cero.
BASELINES = {
    "historial_siniestros": lambda d: d["crashes"].to_numpy(dtype=float),
    "historial_graves": lambda d: d["severe_crashes"].to_numpy(dtype=float) + 1e-4 * d["crashes"].to_numpy(dtype=float),
    "historial_lesionados": lambda d: d["injury_crashes"].to_numpy(dtype=float) + 1e-4 * d["crashes"].to_numpy(dtype=float),
}


def _query(sql: str, params: dict) -> pd.DataFrame:
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return pd.DataFrame(cur.fetchall(), columns=[d.name for d in cur.description])


def build_segment_features(start: date, end: date, segment_id: str | None = None) -> pd.DataFrame:
    if segment_id is None:
        df = _query(FEATURES_SQL, {"start": start, "end": end})
    else:  # una sola cuadra (explicación en la API): se filtra dentro del CTE
        df = _query(SEGMENT_FEATURES_SQL, {"start": start, "end": end, "seg": segment_id})
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


def data_range() -> tuple[date, date]:
    with raw_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT min(crash_date)::date, max(crash_date)::date FROM silver_crashes")
        return cur.fetchone()


def make_windows(anchor: date, first_date: date | None = None) -> dict:
    """Ventanas de 12 meses ancladas en ``anchor`` (exclusivo)."""
    a = pd.Timestamp(anchor)
    m = {k: (a - pd.DateOffset(years=k)).date() for k in (1, 2, 3)}
    if first_date is not None and m[3] < first_date:
        raise ValueError(f"Se necesitan 36 meses de datos antes de {anchor} (desde {m[3]}), pero el primer "
                         f"siniestro es de {first_date}. Ingiera más historia (--since) o use --anchor-date.")
    return {
        "train": ((m[3], m[2]), (m[2], m[1])),
        "test": ((m[2], m[1]), (m[1], a.date())),
        "forecast": (m[1], a.date()),
    }


def preprocessor(scale: bool) -> ColumnTransformer:
    steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scale", StandardScaler()))
    cat = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                    ("onehot", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=50,
                                             sparse_output=False))])
    return ColumnTransformer([("num", Pipeline(steps), NUMERIC), ("cat", cat, CATEGORICAL)])


def make_pipeline(name: str) -> Pipeline:
    # Sin pesos de clase: las probabilidades quedan calibradas y el desbalance se
    # resuelve con el umbral de la clase Alto (elegido fuera de pliegue).
    if name == "logistic_regression":
        model = LogisticRegression(max_iter=2000, C=1.0)
        return Pipeline([("prep", preprocessor(scale=True)), ("model", model)])
    if name == "random_forest":
        model = RandomForestClassifier(n_estimators=400, max_depth=12, min_samples_leaf=10,
                                       n_jobs=os.cpu_count(), random_state=SEED)
        return Pipeline([("prep", preprocessor(scale=False)), ("model", model)])
    if name == "xgboost":
        model = XGBClassifier(objective="multi:softprob", num_class=3, tree_method="hist", n_estimators=400,
                              learning_rate=0.03, max_depth=4, subsample=0.8, colsample_bytree=0.8,
                              min_child_weight=5, n_jobs=os.cpu_count(), random_state=SEED, eval_metric="mlogloss")
        return Pipeline([("prep", preprocessor(scale=False)), ("model", model)])
    raise ValueError(name)


def fit(pipe: Pipeline, X: pd.DataFrame, y: pd.Series) -> Pipeline:
    return pipe.fit(X, y)


def ranking_metrics(y: np.ndarray, score: np.ndarray, future_severe: np.ndarray,
                    top_share: float = TOP_SHARE) -> dict:
    n_top = max(1, int(len(y) * top_share))
    order = np.argsort(-score, kind="stable")
    capture = top_share_capture(score, future_severe, top_share)
    return {
        "auc_roc_high_vs_rest": float(roc_auc_score(y == HIGH, score)),
        "base_rate_high": float((y == HIGH).mean()),
        "top10_precision_high": float((y[order[:n_top]] == HIGH).mean()),
        "top10_capture_severe": capture,
        "top10_lift": capture / top_share,
    }


def evaluate(y: np.ndarray, proba: np.ndarray, future_severe: np.ndarray, threshold: float,
             top_share: float = TOP_SHARE) -> dict:
    pred = decide(proba, HIGH, threshold)
    cal = calibration(y == HIGH, proba[:, HIGH])
    return {
        "auc_roc_ovr_macro": float(roc_auc_score(y, proba, multi_class="ovr", average="macro", labels=[0, 1, 2])),
        **ranking_metrics(y, proba[:, HIGH], future_severe, top_share),
        "threshold_high": float(threshold),
        "recall_high": float(recall_score(y == HIGH, pred == HIGH, zero_division=0)),
        "precision_high": float(precision_score(y == HIGH, pred == HIGH, zero_division=0)),
        "predicted_high_share": float((pred == HIGH).mean()),
        "brier_high": cal["brier"],
        "ece_high": cal["ece"],
    }


def spatial_oof(name: str, X: pd.DataFrame, y: pd.Series, groups: pd.Series) -> tuple[np.ndarray, list[float]]:
    """Predicciones fuera de pliegue con GroupKFold por bloques espaciales de ~2 km."""
    oof = np.zeros((len(X), 3))
    aucs = []
    for tr, va in GroupKFold(n_splits=5).split(X, y, groups):
        pipe = fit(make_pipeline(name), X.iloc[tr], y.iloc[tr])
        oof[va] = pipe.predict_proba(X.iloc[va])
        aucs.append(float(roc_auc_score(y.iloc[va], oof[va], multi_class="ovr", average="macro", labels=[0, 1, 2])))
    return oof, aucs


def spatial_groups(df: pd.DataFrame) -> pd.Series:
    """Bloques de ~2 km (4 x 4 celdas de 500 m); cuadras sin geometría van a su propio grupo."""
    gx, gy = df["gx"].fillna(-1e9), df["gy"].fillna(-1e9)
    return (gx // 4).astype(np.int64).astype(str) + "_" + (gy // 4).astype(np.int64).astype(str)


def importance(pipe: Pipeline, top: int = 15) -> list[dict]:
    names = pipe.named_steps["prep"].get_feature_names_out()
    model = pipe.named_steps["model"]
    imp = np.abs(model.coef_).mean(axis=0) if hasattr(model, "coef_") else model.feature_importances_
    order = np.argsort(imp)[::-1][:top]
    return [{"feature": str(names[i]).split("__", 1)[-1], "importance": float(imp[i])} for i in order]


def _window_str(w: tuple[tuple[date, date], tuple[date, date]]) -> str:
    (h0, h1), (t0, t1) = w
    return f"historia {h0} -> {h1} | riesgo {t0} -> {t1}"


def run(model_path: str = SEGMENT_MODEL_PATH, anchor: date | None = None, bootstrap_reps: int = 500) -> dict:
    t0 = time.perf_counter()
    first, last = data_range()
    anchor = anchor or (pd.Timestamp(last) + pd.Timedelta(days=1)).date()
    w = make_windows(anchor, first)
    train = build_dataset(*w["train"])
    test = build_dataset(*w["test"])
    logger.info("Ventanas %s | tramos train=%d test=%d | clases train %s", w, len(train), len(test),
                train["target"].value_counts(normalize=True).round(3).to_dict())

    groups = spatial_groups(train)
    y_tr, y_te = train["target"], test["target"].to_numpy()
    fs_tr, fs_te = train["future_severe"].to_numpy(), test["future_severe"].to_numpy()
    report: dict = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "unit": "cuadra (centena de número + dirección + calle)",
        "anchor_date": str(anchor),
        "data_range": [str(first), str(last)],
        "windows": {"train": _window_str(w["train"]), "test": _window_str(w["test"])},
        "n_train": int(len(train)), "n_test": int(len(test)),
        "class_distribution_train": {SEGMENT_LABELS[k]: float(v) for k, v in
                                     train["target"].value_counts(normalize=True).items()},
        "class_distribution_test": {SEGMENT_LABELS[k]: float(v) for k, v in
                                    test["target"].value_counts(normalize=True).items()},
        "decision_rule": "Alto si P(Alto) >= umbral F1 fuera de pliegue; si no, la más probable entre Bajo y Medio",
        "models": {},
    }

    # 1) CV espacial en train: AUC por pliegue + predicciones fuera de pliegue,
    #    con las que se fija el umbral y se elige el ganador (sin mirar el test)
    oof_scores: dict[str, np.ndarray] = {}
    test_scores: dict[str, np.ndarray] = {}
    fitted: dict = {}
    for name in MODEL_ORDER:
        oof, aucs = spatial_oof(name, train[FEATURES], y_tr, groups)
        thr = f1_threshold((y_tr == HIGH).to_numpy(), oof[:, HIGH])
        a = np.array(aucs)
        oof_eval = evaluate(y_tr.to_numpy(), oof, fs_tr, thr)
        pipe = fit(make_pipeline(name), train[FEATURES], y_tr)
        proba = pipe.predict_proba(test[FEATURES])
        m = evaluate(y_te, proba, fs_te, thr)
        report["models"][name] = {
            "spatial_cv": {"auc_folds": aucs, "auc_mean": float(a.mean()), "auc_std": float(a.std()),
                           "auc_cv_variation": float(a.std() / a.mean()),
                           "oof_top10_capture_severe": oof_eval["top10_capture_severe"],
                           "oof_threshold_high": thr},
            "temporal_test": m,
            "calibration_high": calibration(y_te == HIGH, proba[:, HIGH]),
            "confusion_matrix": confusion_matrix(y_te, decide(proba, HIGH, thr), labels=[0, 1, 2]).tolist(),
            "feature_importance": importance(pipe),
        }
        oof_scores[name], test_scores[name] = oof[:, HIGH], proba[:, HIGH]
        fitted[name] = pipe
        logger.info("[%s] CV espacial AUC %.3f ± %.3f | captura OOF %.3f | test %s", name, a.mean(), a.std(),
                    oof_eval["top10_capture_severe"], {k: round(v, 3) for k, v in m.items()})

    # 2) Selección: captura top 10 % fuera de pliegue, con la regla de un error
    #    estándar (bootstrap) a favor del modelo más simple
    oof_boot = bootstrap_capture(oof_scores, fs_tr, TOP_SHARE, reps=max(100, bootstrap_reps // 2))
    best = max(MODEL_ORDER, key=lambda k: oof_boot[k]["capture"])
    tol = oof_boot[best]["capture"] - oof_boot[best]["se"]
    winner = next(k for k in MODEL_ORDER if oof_boot[k]["capture"] >= tol)
    report["selection_metric"] = "oof_top10_capture_severe (CV espacial en train, regla de 1 error estándar)"
    report["selection"] = {k: {"capture": oof_boot[k]["capture"], "se": oof_boot[k]["se"]} for k in MODEL_ORDER}
    report["winner"] = winner
    report["baseline_gain_auc"] = (report["models"][winner]["temporal_test"]["auc_roc_ovr_macro"]
                                   - report["models"]["logistic_regression"]["temporal_test"]["auc_roc_ovr_macro"])

    # 3) Test temporal (una sola vez): líneas base heurísticas e IC 95 % bootstrap
    report["baselines"] = {}
    for name, fn in BASELINES.items():
        score = fn(test)
        test_scores[name] = score
        report["baselines"][name] = ranking_metrics(y_te, score, fs_te)
    boot = bootstrap_capture(test_scores, fs_te, TOP_SHARE, reps=bootstrap_reps)
    best_baseline = max(BASELINES, key=lambda k: boot[k]["capture"])
    report["bootstrap_top10_capture"] = {k: {kk: vv for kk, vv in v.items()} for k, v in boot.items()
                                         if not k.startswith("_")}
    report["winner_vs_best_baseline"] = {"baseline": best_baseline, **paired_diff(boot, winner, best_baseline)}
    logger.info("Ganador %s vs mejor línea base %s: %s", winner, best_baseline, report["winner_vs_best_baseline"])

    # 4) Modelo de producción: ganador reentrenado con la ventana más reciente con
    #    etiqueta completa (la de test); su umbral sale de su propia CV espacial.
    final = fit(make_pipeline(winner), test[FEATURES], test["target"])
    oof_final, _ = spatial_oof(winner, test[FEATURES], test["target"], spatial_groups(test))
    final_thr = f1_threshold(y_te == HIGH, oof_final[:, HIGH])
    hist_start, hist_end = w["forecast"]
    current = build_segment_features(hist_start, hist_end)
    p = final.predict_proba(current[FEATURES])
    current["p_bajo"], current["p_medio"], current["p_alto"] = p[:, 0], p[:, 1], p[:, 2]
    current["risk_class"] = decide(p, HIGH, final_thr)
    current["priority_rank"] = current["p_alto"].rank(ascending=False, method="first").astype(int)
    current["priority_pct"] = current["priority_rank"] / len(current)
    out_cols = ["segment_id", "lat", "lon", "crashes", "injury_crashes", "severe_crashes", "fatalities",
                "ped_crashes", "bike_crashes", "mean_speed", "mean_aadt", "workzone_share", "p_bajo", "p_medio",
                "p_alto", "risk_class", "priority_rank", "priority_pct"]
    scored = current[out_cols].sort_values("priority_rank")
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    scored.to_parquet(settings.processed_dir / "gold_segment_risk.parquet", index=False)
    report["forecast"] = {
        "history_window": f"{hist_start} -> {hist_end}",
        "segments_scored": int(len(scored)),
        "high_risk_segments": int((scored["risk_class"] == HIGH).sum()),
        "high_risk_threshold": final_thr,
        "trained_on": report["windows"]["test"],
        "top10": scored.head(10)[["segment_id", "p_alto", "severe_crashes", "crashes"]].round(3).to_dict(orient="records"),
    }
    report["provenance"] = provenance(train[["segment_id", "target"]])

    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": final, "meta": {"algorithm": winner, "features": FEATURES, "classes": SEGMENT_LABELS,
                                             "trained_at": report["trained_at"], "high_threshold": final_thr,
                                             "anchor_date": str(anchor), "provenance": report["provenance"]}},
                model_path, compress=3)
    try:
        from app.services.olap.duckdb_engine import attach_table
        attach_table("gold_segment_risk", scored)
    except Exception as exc:  # DuckDB bloqueado o inexistente: queda el Parquet para el próximo export
        logger.warning("No se pudo adjuntar gold_segment_risk a DuckDB (%s); se usará el Parquet en el próximo "
                       "export de la Capa Gold", exc)
        report["attach_error"] = str(exc)

    report["elapsed_s"] = round(time.perf_counter() - t0, 1)
    text = json.dumps(report, indent=2, default=str)
    (settings.processed_dir / "segment_model_report.json").write_text(text, encoding="utf-8")
    Path(model_path).with_name("segment_model_report.json").write_text(text, encoding="utf-8")
    logger.info("Ganador: %s | ganancia AUC sobre la línea base: %+.3f", winner, report["baseline_gain_auc"])
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Modelo de riesgo por tramo vial")
    parser.add_argument("--model-path", default=SEGMENT_MODEL_PATH)
    parser.add_argument("--anchor-date", type=date.fromisoformat, default=None,
                        help="Fin (exclusivo) de la última ventana; por defecto, el día después del último siniestro")
    parser.add_argument("--bootstrap-reps", type=int, default=500)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    r = run(args.model_path, args.anchor_date, args.bootstrap_reps)
    print(json.dumps({k: r[k] for k in ("winner", "windows", "selection", "winner_vs_best_baseline",
                                        "class_distribution_test")}, indent=2, default=str))
    for name, m in r["models"].items():
        print(name, json.dumps({"cv": round(m["spatial_cv"]["auc_mean"], 3),
                                **{k: round(v, 3) for k, v in m["temporal_test"].items()}}))
    for name, m in r["baselines"].items():
        print(name, json.dumps({k: round(v, 3) for k, v in m.items()}))


if __name__ == "__main__":
    main()
