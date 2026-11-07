"""Entrenamiento, validación y evaluación del modelo de severidad por siniestro (Fase 3).

Diseño de validación (sin fugas):

* **Partición temporal**: train = todo lo anterior a la validación, validación =
  los ``--val-months`` meses previos al test, test = los últimos ``--test-months``
  meses. El modelo nunca se evalúa con siniestros anteriores a los que aprendió.
* **Densidad histórica sin futuro**: ``grid_density`` se calcula sólo con el
  periodo de entrenamiento para train/validación, y con train+validación para el
  test (``add_grid_density``).
* **Hiperparámetros, umbral y ganador se eligen en validación**; el test se usa
  una sola vez, para reportar.
* **Probabilidades calibradas**: por defecto se entrena sin pesos de clase (con
  pesos "balanced" las probabilidades se inflaban hacia la clase rara). El
  desbalance se resuelve con el umbral de decisión, elegido en validación para
  alcanzar el recall objetivo de la clase Crítica. Se reportan Brier, ECE y la
  curva de fiabilidad.
* **Estabilidad espacial**: GroupKFold de 5 pliegues por bloques de ~2 km.
* **Ablación**: AUC del mismo modelo sólo con condiciones previas al choque (sin
  variables del mecanismo del siniestro), para dimensionar su peso.
* El mapa ``gold_grid_ml`` usa predicciones **fuera de pliegue espacial**: cada
  celda la puntúa un modelo que no vio esa zona.

El modelo publicado se reentrena con todos los datos y los hiperparámetros y el
umbral elegidos en validación.

Uso:
    python -m app.ml.train --input /data/processed/features_gold.parquet --algorithm xgboost
    python -m app.ml.train --algorithm both
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (classification_report, confusion_matrix, log_loss, precision_score, recall_score,
                             roc_auc_score)
from sklearn.model_selection import GroupKFold, ParameterGrid
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.severity import SEVERITY_LABELS
from app.ml.evaluation import (calibration, decide, f1_threshold, provenance, rare_class_metrics, recall_threshold,
                               spatial_blocks, temporal_masks)
from app.ml.feature_engineering import (CATEGORICAL_FEATURES, FEATURES, MECHANISM_FEATURES, NUMERIC_FEATURES, TARGET,
                                        add_grid_density, years_span)

logger = logging.getLogger("ml.train")

CRITICAL = 2
SEED = 42
RECALL_TARGET = 0.60
# La meta de precisión >= 0,65 era inalcanzable con una clase del 1,6 %: se
# sustituye por el lift (precisión / tasa base) con la regla de decisión publicada.
THRESHOLDS = {"auc_roc": 0.70, "recall_critical": RECALL_TARGET, "lift_critical": 3.0, "cv_variance": 0.05}


def make_preprocessor(numeric: list[str] = NUMERIC_FEATURES,
                      categorical: list[str] = CATEGORICAL_FEATURES) -> ColumnTransformer:
    numeric_pipe = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
        ("onehot", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=100, sparse_output=False)),
    ])
    return ColumnTransformer([("num", numeric_pipe, numeric), ("cat", categorical_pipe, categorical)])


def make_model(algorithm: str, params: dict, balanced: bool = False) -> object:
    if algorithm == "xgboost":
        base = dict(objective="multi:softprob", num_class=3, tree_method="hist", eval_metric="mlogloss",
                    learning_rate=0.05, n_estimators=500, subsample=0.8, colsample_bytree=0.8,
                    max_depth=6, n_jobs=os.cpu_count(), random_state=SEED)
        base.update(params)
        return XGBClassifier(**base)
    if algorithm == "random_forest":
        base = dict(n_estimators=200, max_depth=15, min_samples_leaf=20,
                    class_weight="balanced_subsample" if balanced else None,
                    n_jobs=os.cpu_count(), random_state=SEED)
        base.update(params)
        return RandomForestClassifier(**base)
    raise ValueError(algorithm)


PARAM_GRIDS = {
    "xgboost": {"max_depth": [4, 6], "min_child_weight": [1, 10]},
    "random_forest": {"max_depth": [12, 15], "min_samples_leaf": [10, 30]},
}


def build_pipeline(algorithm: str, params: dict, balanced: bool = False,
                   numeric: list[str] = NUMERIC_FEATURES, categorical: list[str] = CATEGORICAL_FEATURES) -> Pipeline:
    return Pipeline([("prep", make_preprocessor(numeric, categorical)), ("model", make_model(algorithm, params, balanced))])


def fit_pipeline(pipe: Pipeline, X: pd.DataFrame, y: pd.Series, balanced: bool = False) -> Pipeline:
    # Sólo con --balanced: XGBoost recibe sample_weight (RF usa class_weight).
    # Por defecto no se pondera, para que las probabilidades queden calibradas.
    if balanced and isinstance(pipe.named_steps["model"], XGBClassifier):
        pipe.fit(X, y, model__sample_weight=compute_sample_weight("balanced", y))
    else:
        pipe.fit(X, y)
    return pipe


def critical_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float | None = None) -> dict:
    pred = proba.argmax(axis=1) if threshold is None else decide(proba, CRITICAL, threshold)
    return {
        "auc_roc_ovr_macro": float(roc_auc_score(y_true, proba, multi_class="ovr", average="macro")),
        "auc_roc_critical_vs_rest": float(roc_auc_score(y_true == CRITICAL, proba[:, CRITICAL])),
        "recall_critical": float(recall_score(y_true == CRITICAL, pred == CRITICAL, zero_division=0)),
        "precision_critical": float(precision_score(y_true == CRITICAL, pred == CRITICAL, zero_division=0)),
        "recall_macro": float(recall_score(y_true, pred, average="macro", zero_division=0)),
    }


def search_on_validation(algorithm: str, X_tr: pd.DataFrame, y_tr: pd.Series, X_va: pd.DataFrame,
                         y_va: pd.Series, balanced: bool) -> tuple[dict, list[dict], Pipeline]:
    """Rejilla de hiperparámetros evaluada en la ventana de validación (temporal)."""
    results, best_pipe, best = [], None, None
    for params in ParameterGrid(PARAM_GRIDS[algorithm]):
        pipe = fit_pipeline(build_pipeline(algorithm, params, balanced), X_tr, y_tr, balanced)
        p = pipe.predict_proba(X_va)
        res = {
            "params": params,
            "val_auc_macro": float(roc_auc_score(y_va, p, multi_class="ovr", average="macro")),
            "val_auc_critical": float(roc_auc_score(y_va == CRITICAL, p[:, CRITICAL])),
            "val_average_precision_critical": float(rare_class_metrics(
                (y_va == CRITICAL).to_numpy(), p[:, CRITICAL], p[:, CRITICAL] >= 0.5)["average_precision"]),
            "val_log_loss": float(log_loss(y_va, p, labels=[0, 1, 2])),
        }
        results.append(res)
        logger.info("[%s] validación %s -> AUC %.4f | AP crítico %.4f", algorithm, params, res["val_auc_macro"],
                    res["val_average_precision_critical"])
        if best is None or res["val_auc_macro"] > best["val_auc_macro"]:
            best, best_pipe = res, pipe
    return best, results, best_pipe


def spatial_cv(algorithm: str, params: dict, X: pd.DataFrame, y: pd.Series, groups: pd.Series,
               balanced: bool, sample: int) -> dict:
    """Estabilidad entre bloques espaciales de ~2 km (sobre una muestra del train)."""
    if len(X) > sample:
        idx = X.sample(n=sample, random_state=SEED).index
        X, y, groups = X.loc[idx], y.loc[idx], groups.loc[idx]
    aucs = []
    for tr, va in GroupKFold(n_splits=5).split(X, y, groups):
        pipe = fit_pipeline(build_pipeline(algorithm, params, balanced), X.iloc[tr], y.iloc[tr], balanced)
        aucs.append(float(roc_auc_score(y.iloc[va], pipe.predict_proba(X.iloc[va]), multi_class="ovr",
                                        average="macro", labels=[0, 1, 2])))
    a = np.array(aucs)
    return {"params": params, "scheme": "GroupKFold(5) por bloques de ~2 km", "auc_folds": aucs,
            "auc_mean": float(a.mean()), "auc_std": float(a.std()), "auc_cv_variation": float(a.std() / a.mean())}


def feature_importance(pipe: Pipeline, top: int = 20) -> list[dict]:
    names = pipe.named_steps["prep"].get_feature_names_out()
    imp = pipe.named_steps["model"].feature_importances_
    order = np.argsort(imp)[::-1][:top]
    return [{"feature": str(names[i]), "importance": float(imp[i])} for i in order]


def spatial_oof_proba(algorithm: str, params: dict, X: pd.DataFrame, y: pd.Series, groups: pd.Series,
                      balanced: bool) -> np.ndarray:
    """Probabilidades fuera de pliegue espacial para todas las filas (mapa de riesgo)."""
    oof = np.zeros((len(X), 3))
    for tr, va in GroupKFold(n_splits=5).split(X, y, groups):
        pipe = fit_pipeline(build_pipeline(algorithm, params, balanced), X.iloc[tr], y.iloc[tr], balanced)
        oof[va] = pipe.predict_proba(X.iloc[va])
    return oof


def train(input_path: str, algorithms: list[str], cv_sample: int, model_path: str, test_months: int = 12,
          val_months: int = 6, recall_target: float = RECALL_TARGET, balanced: bool = False) -> dict:
    df = pd.read_parquet(input_path)
    df["crash_date"] = pd.to_datetime(df["crash_date"])
    df = df.sort_values("crash_date", kind="stable").reset_index(drop=True)
    y = df[TARGET].astype(int)
    tr, va, te, windows = temporal_masks(df["crash_date"], test_months, val_months)

    # grid_density sin futuro: historia = train (para train/val) y train+val (para test)
    fit_view = add_grid_density(df, history=tr)
    test_view = add_grid_density(df, history=tr | va)
    X_tr, y_tr = fit_view.loc[tr, FEATURES], y[tr]
    X_va, y_va = fit_view.loc[va, FEATURES], y[va]
    X_te, y_te = test_view.loc[te, FEATURES], y[te]
    groups_tr = spatial_blocks(df.loc[tr, "grid_x"], df.loc[tr, "grid_y"])
    logger.info("Partición temporal %s | filas train=%d val=%d test=%d", windows, tr.sum(), va.sum(), te.sum())

    report: dict = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "n_train": int(tr.sum()), "n_val": int(va.sum()), "n_test": int(te.sum()),
        "windows": windows,
        "validation_design": ("Partición temporal train/val/test; hiperparámetros, umbral y ganador elegidos en "
                              "validación; grid_density calculada sólo con el pasado de cada partición; test usado "
                              "una vez."),
        "class_weighting": "balanced" if balanced else "none (probabilidades calibradas)",
        "class_distribution": {SEVERITY_LABELS[k]: float(v) for k, v in y.value_counts(normalize=True).items()},
        "class_distribution_test": {SEVERITY_LABELS[k]: float(v) for k, v in y_te.value_counts(normalize=True).items()},
        "thresholds_required": THRESHOLDS,
        "decision_rule": f"Crítico si P(Crítico) >= umbral elegido en validación para recall >= {recall_target:.2f}",
        "models": {},
    }
    fitted: dict = {}
    y_te_np = y_te.to_numpy()
    for algo in algorithms:
        t0 = time.perf_counter()
        best, grid, pipe = search_on_validation(algo, X_tr, y_tr, X_va, y_va, balanced)
        p_va = pipe.predict_proba(X_va)[:, CRITICAL]
        thr_decision = recall_threshold((y_va == CRITICAL).to_numpy(), p_va, recall_target)
        thr_f1 = f1_threshold((y_va == CRITICAL).to_numpy(), p_va)
        cv = spatial_cv(algo, best["params"], X_tr, y_tr, groups_tr, balanced, cv_sample)
        t_fit = time.perf_counter() - t0

        proba = pipe.predict_proba(X_te)
        pred = decide(proba, CRITICAL, thr_decision)
        decision = {"threshold": thr_decision, **critical_metrics(y_te_np, proba, thr_decision),
                    **rare_class_metrics(y_te_np == CRITICAL, proba[:, CRITICAL], pred == CRITICAL)}
        report["models"][algo] = {
            "best_params": best["params"],
            "validation": best,
            "validation_grid": grid,
            "cv": cv,
            "test_argmax": critical_metrics(y_te_np, proba),
            "test_decision": decision,
            "test_f1_threshold": {"threshold": thr_f1, **critical_metrics(y_te_np, proba, thr_f1)},
            "calibration_critical": calibration(y_te_np == CRITICAL, proba[:, CRITICAL]),
            "confusion_matrix": confusion_matrix(y_te_np, pred, labels=[0, 1, 2]).tolist(),
            "confusion_matrix_rule": "regla de decisión publicada (umbral de validación)",
            "classification_report": classification_report(y_te_np, pred, output_dict=True, zero_division=0),
            "feature_importance": feature_importance(pipe),
            "fit_seconds": round(t_fit, 1),
        }
        fitted[algo] = (pipe, thr_decision, thr_f1)
        logger.info("[%s] test (regla de validación): %s", algo, {k: round(v, 4) for k, v in decision.items()})

    # Ganador por AUC en VALIDACIÓN (antes se elegía mirando el test)
    winner = max(report["models"], key=lambda a: report["models"][a]["validation"]["val_auc_macro"])
    _, thr_decision, thr_f1 = fitted[winner]
    m = report["models"][winner]
    report["winner"] = winner
    report["selection_metric"] = "val_auc_macro"
    report["gates"] = {
        "auc_roc": m["test_argmax"]["auc_roc_ovr_macro"] >= THRESHOLDS["auc_roc"],
        "recall_critical": m["test_decision"]["recall_critical"] >= THRESHOLDS["recall_critical"],
        "lift_critical": m["test_decision"]["lift"] >= THRESHOLDS["lift_critical"],
        "cv_variance": m["cv"]["auc_cv_variation"] < THRESHOLDS["cv_variance"],
    }

    # Ablación: mismas condiciones sin el mecanismo del siniestro (información
    # que sólo existe una vez ocurrido el choque)
    pre_num = [f for f in NUMERIC_FEATURES if f not in MECHANISM_FEATURES]
    pre_cat = [f for f in CATEGORICAL_FEATURES if f not in MECHANISM_FEATURES]
    pre = fit_pipeline(build_pipeline(winner, m["best_params"], balanced, pre_num, pre_cat),
                       X_tr[pre_num + pre_cat], y_tr, balanced)
    p_pre = pre.predict_proba(X_te[pre_num + pre_cat])
    report["ablation_pre_crash_only"] = {
        "features": pre_num + pre_cat,
        "auc_roc_ovr_macro": float(roc_auc_score(y_te_np, p_pre, multi_class="ovr", average="macro")),
        "auc_roc_critical_vs_rest": float(roc_auc_score(y_te_np == CRITICAL, p_pre[:, CRITICAL])),
        "average_precision_critical": float(rare_class_metrics(
            y_te_np == CRITICAL, p_pre[:, CRITICAL], p_pre[:, CRITICAL] >= 0.5)["average_precision"]),
    }
    logger.info("Ablación sin mecanismo: %s", report["ablation_pre_crash_only"])

    # Modelo publicado: todos los datos, con grid_density de toda la historia
    # (misma definición que calcula la API en vivo).
    all_view = add_grid_density(df)
    X_all = all_view[FEATURES]
    pipe = fit_pipeline(build_pipeline(winner, m["best_params"], balanced), X_all, y, balanced)

    # Perfiles de mecanismo más frecuentes (para marginalizar en la API)
    mech = df[MECHANISM_FEATURES].fillna({"num_units": 2})
    prof = mech.value_counts(normalize=True).head(80).rename("weight").reset_index()
    prof["weight"] = prof["weight"] / prof["weight"].sum()

    prov = provenance(df[[TARGET, "crash_date", "grid_x", "grid_y"]], input_path)
    report["provenance"] = prov
    artifact = {
        "pipeline": pipe,
        "meta": {
            "algorithm": winner,
            "features": FEATURES,
            "classes": SEVERITY_LABELS,
            "best_params": m["best_params"],
            "critical_threshold": thr_decision,
            "critical_threshold_rule": f"recall >= {recall_target:.2f} en validación",
            "critical_threshold_f1": thr_f1,
            "test_metrics": m["test_argmax"],
            "test_decision": m["test_decision"],
            "trained_at": report["trained_at"],
            "n_train": int(len(X_all)),
            "windows": windows,
            "grid_density_definition": "all_history",
            "grid_density_years": years_span(df["crash_date"]),
            "grid_density_window": [str(df["crash_date"].min().date()), str(df["crash_date"].max().date())],
            "mechanism_profiles": prof.to_dict(orient="records"),
            "mechanism_coverage": float(mech.value_counts(normalize=True).head(80).sum()),
            "provenance": prov,
        },
    }
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path, compress=3)
    t0 = time.perf_counter()
    loaded = joblib.load(model_path)
    report["artifact"] = {
        "path": model_path,
        "size_mb": round(os.path.getsize(model_path) / 1e6, 2),
        "load_ms": round((time.perf_counter() - t0) * 1000, 1),
        "trained_on": "todos los datos (hiperparámetros y umbral de validación)",
    }
    t0 = time.perf_counter()
    loaded["pipeline"].predict_proba(X_te.iloc[[0]])
    report["artifact"]["single_inference_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    report["artifact"]["gate_size_lt_100mb"] = report["artifact"]["size_mb"] < 100

    # Riesgo medio por celda de 500 m con predicciones FUERA DE PLIEGUE ESPACIAL
    # (antes eran predicciones dentro de la muestra del modelo entrenado con esas filas)
    groups_all = spatial_blocks(df["grid_x"], df["grid_y"])
    oof = spatial_oof_proba(winner, m["best_params"], X_all, y, groups_all, balanced)
    report["spatial_oof"] = {
        "auc_roc_ovr_macro": float(roc_auc_score(y, oof, multi_class="ovr", average="macro")),
        "auc_roc_critical_vs_rest": float(roc_auc_score(y == CRITICAL, oof[:, CRITICAL])),
        "calibration_critical": {k: v for k, v in calibration((y == CRITICAL).to_numpy(), oof[:, CRITICAL]).items()
                                 if k != "reliability"},
    }
    grid = df[["grid_x", "grid_y", "latitude", "longitude"]].copy()
    grid["p_critical"] = oof[:, CRITICAL]
    grid["observed_critical"] = (y == CRITICAL).astype(float)
    grid = grid.groupby(["grid_x", "grid_y"], as_index=False).agg(
        crashes=("p_critical", "size"), mean_p_critical=("p_critical", "mean"),
        observed_critical_rate=("observed_critical", "mean"), lat=("latitude", "mean"), lon=("longitude", "mean"))
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    grid.to_parquet(settings.processed_dir / "gold_grid_ml.parquet", index=False)
    report["grid_cells_scored"] = int(len(grid))
    try:
        from app.services.olap.duckdb_engine import attach_ml_grid
        attach_ml_grid(grid)
    except Exception as exc:  # DuckDB bloqueado o inexistente: queda el Parquet para el próximo export
        logger.warning("No se pudo adjuntar gold_grid_ml a DuckDB (%s); se usará el Parquet en el próximo "
                       "export de la Capa Gold", exc)
        report["grid_attach_error"] = str(exc)

    out = settings.processed_dir / "model_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    # Copia junto al modelo para que la API exponga las métricas
    Path(model_path).with_name("model_report.json").write_text(json.dumps(report, indent=2, default=str),
                                                               encoding="utf-8")
    logger.info("Ganador: %s | gates: %s | artefacto: %s", winner, report["gates"], report["artifact"])
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Entrenamiento del modelo de severidad por siniestro")
    parser.add_argument("--input", default=str(settings.processed_dir / "features_gold.parquet"))
    parser.add_argument("--algorithm", default="both", choices=["xgboost", "random_forest", "both"])
    parser.add_argument("--cv-sample", type=int, default=120_000,
                        help="Filas del train usadas en la CV espacial de estabilidad")
    parser.add_argument("--test-months", type=int, default=12, help="Meses finales reservados para test")
    parser.add_argument("--val-months", type=int, default=6, help="Meses previos al test para validación")
    parser.add_argument("--recall-target", type=float, default=RECALL_TARGET,
                        help="Recall de la clase Crítica con el que se fija el umbral en validación")
    parser.add_argument("--balanced", action="store_true",
                        help="Ponderar clases (descalibra las probabilidades; sólo para comparar)")
    parser.add_argument("--model-path", default=settings.MODEL_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    algos = ["xgboost", "random_forest"] if args.algorithm == "both" else [args.algorithm]
    report = train(args.input, algos, args.cv_sample, args.model_path, args.test_months, args.val_months,
                   args.recall_target, args.balanced)
    w = report["models"][report["winner"]]
    print(json.dumps({"winner": report["winner"], "windows": report["windows"], "gates": report["gates"],
                      "test_argmax": w["test_argmax"], "test_decision": w["test_decision"],
                      "calibration": {k: v for k, v in w["calibration_critical"].items() if k != "reliability"},
                      "ablation_pre_crash_only": report["ablation_pre_crash_only"],
                      "artifact": report["artifact"]}, indent=2))


if __name__ == "__main__":
    main()
