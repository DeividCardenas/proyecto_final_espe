"""Entrenamiento, validación cruzada y evaluación de modelos de riesgo (Fase 3).

* Partición estratificada 80/20 (hold-out).
* Desbalance tratado con ponderación de clases (sin sobremuestreo sintético).
* Random Forest y XGBoost; búsqueda de hiperparámetros con StratifiedKFold (5).
* Métricas en test: AUC-ROC multiclase (OvR macro), recall y precisión de la
  clase Crítica, matriz de confusión e importancia de características.
* Serializa el pipeline ganador (preprocesador + modelo) con joblib.

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
from sklearn.metrics import (classification_report, confusion_matrix, precision_recall_curve,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import ParameterGrid, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from app.core.config import settings
from app.core.severity import SEVERITY_LABELS
from app.ml.feature_engineering import (CATEGORICAL_FEATURES, FEATURES, MECHANISM_FEATURES, NUMERIC_FEATURES,
                                        TARGET)

logger = logging.getLogger("ml.train")

CRITICAL = 2
SEED = 42
THRESHOLDS = {"auc_roc": 0.70, "recall_critical": 0.60, "precision_critical": 0.65, "cv_variance": 0.05}


def make_preprocessor() -> ColumnTransformer:
    numeric = Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
        ("onehot", OneHotEncoder(handle_unknown="infrequent_if_exist", min_frequency=100, sparse_output=False)),
    ])
    return ColumnTransformer([("num", numeric, NUMERIC_FEATURES), ("cat", categorical, CATEGORICAL_FEATURES)])


def make_model(algorithm: str, params: dict) -> object:
    if algorithm == "xgboost":
        base = dict(objective="multi:softprob", num_class=3, tree_method="hist", eval_metric="mlogloss",
                    learning_rate=0.05, n_estimators=500, subsample=0.8, colsample_bytree=0.8,
                    max_depth=6, n_jobs=os.cpu_count(), random_state=SEED)
        base.update(params)
        return XGBClassifier(**base)
    if algorithm == "random_forest":
        base = dict(n_estimators=200, max_depth=15, min_samples_leaf=20, class_weight="balanced_subsample",
                    n_jobs=os.cpu_count(), random_state=SEED)
        base.update(params)
        return RandomForestClassifier(**base)
    raise ValueError(algorithm)


PARAM_GRIDS = {
    "xgboost": {"max_depth": [4, 6], "min_child_weight": [1, 10]},
    "random_forest": {"max_depth": [12, 15], "min_samples_leaf": [10, 30]},
}


def build_pipeline(algorithm: str, params: dict) -> Pipeline:
    return Pipeline([("prep", make_preprocessor()), ("model", make_model(algorithm, params))])


def fit_pipeline(pipe: Pipeline, X: pd.DataFrame, y: pd.Series) -> Pipeline:
    # Ponderación balanceada: XGBoost la recibe como sample_weight (equivalente
    # multiclase de scale_pos_weight); RF usa class_weight internamente.
    if isinstance(pipe.named_steps["model"], XGBClassifier):
        pipe.fit(X, y, model__sample_weight=compute_sample_weight("balanced", y))
    else:
        pipe.fit(X, y)
    return pipe


def critical_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float | None = None) -> dict:
    pred = proba.argmax(axis=1) if threshold is None else np.where(proba[:, CRITICAL] >= threshold, CRITICAL,
                                                                    proba[:, :CRITICAL].argmax(axis=1))
    return {
        "auc_roc_ovr_macro": float(roc_auc_score(y_true, proba, multi_class="ovr", average="macro")),
        "auc_roc_critical_vs_rest": float(roc_auc_score(y_true == CRITICAL, proba[:, CRITICAL])),
        "recall_critical": float(recall_score(y_true == CRITICAL, pred == CRITICAL, zero_division=0)),
        "precision_critical": float(precision_score(y_true == CRITICAL, pred == CRITICAL, zero_division=0)),
        "recall_macro": float(recall_score(y_true, pred, average="macro", zero_division=0)),
    }


def cross_validate(algorithm: str, X: pd.DataFrame, y: pd.Series, cv_sample: int) -> tuple[dict, list[dict]]:
    if len(X) > cv_sample:
        X, _, y, _ = train_test_split(X, y, train_size=cv_sample, stratify=y, random_state=SEED)
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    results = []
    for params in ParameterGrid(PARAM_GRIDS[algorithm]):
        folds = []
        for tr, va in skf.split(X, y):
            pipe = fit_pipeline(build_pipeline(algorithm, params), X.iloc[tr], y.iloc[tr])
            folds.append(critical_metrics(y.iloc[va].to_numpy(), pipe.predict_proba(X.iloc[va])))
        aucs = np.array([f["auc_roc_ovr_macro"] for f in folds])
        res = {
            "params": params,
            "auc_mean": float(aucs.mean()),
            "auc_std": float(aucs.std()),
            # Variación relativa entre pliegues (coeficiente de variación)
            "auc_cv_variation": float(aucs.std() / aucs.mean()),
            "recall_critical_mean": float(np.mean([f["recall_critical"] for f in folds])),
            "folds": folds,
        }
        results.append(res)
        logger.info("[%s] CV %s -> AUC %.4f ± %.4f", algorithm, params, res["auc_mean"], res["auc_std"])
    best = max(results, key=lambda r: r["auc_mean"])
    return best, results


def feature_importance(pipe: Pipeline, top: int = 20) -> list[dict]:
    names = pipe.named_steps["prep"].get_feature_names_out()
    imp = pipe.named_steps["model"].feature_importances_
    order = np.argsort(imp)[::-1][:top]
    return [{"feature": str(names[i]), "importance": float(imp[i])} for i in order]


def best_f1_threshold(y_true: np.ndarray, p_critical: np.ndarray) -> float:
    prec, rec, thr = precision_recall_curve(y_true == CRITICAL, p_critical)
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    return float(thr[np.nanargmax(f1[:-1])])


def train(input_path: str, algorithms: list[str], cv_sample: int, model_path: str) -> dict:
    df = pd.read_parquet(input_path)
    X, y = df[FEATURES], df[TARGET].astype(int)
    logger.info("Dataset: %d filas; distribución %s", len(df), y.value_counts(normalize=True).round(4).to_dict())
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)

    report: dict = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "class_distribution": {SEVERITY_LABELS[k]: float(v) for k, v in y.value_counts(normalize=True).items()},
        "thresholds_required": THRESHOLDS,
        "models": {},
    }
    fitted = {}
    for algo in algorithms:
        t0 = time.perf_counter()
        best, all_cv = cross_validate(algo, X_train, y_train, cv_sample)
        pipe = fit_pipeline(build_pipeline(algo, best["params"]), X_train, y_train)
        t_fit = time.perf_counter() - t0
        proba = pipe.predict_proba(X_test)
        y_np = y_test.to_numpy()
        argmax_metrics = critical_metrics(y_np, proba)
        thr = best_f1_threshold(y_np, proba[:, CRITICAL])
        tuned_metrics = critical_metrics(y_np, proba, threshold=thr)
        pred = proba.argmax(axis=1)
        report["models"][algo] = {
            "best_params": best["params"],
            "cv": {k: v for k, v in best.items() if k != "folds"},
            "cv_folds": best["folds"],
            "cv_grid": [{k: v for k, v in r.items() if k != "folds"} for r in all_cv],
            "test_argmax": argmax_metrics,
            "test_f1_threshold": {"threshold": thr, **tuned_metrics},
            "confusion_matrix": confusion_matrix(y_np, pred).tolist(),
            "classification_report": classification_report(y_np, pred, output_dict=True, zero_division=0),
            "feature_importance": feature_importance(pipe),
            "fit_seconds": round(t_fit, 1),
        }
        fitted[algo] = (pipe, thr)
        logger.info("[%s] test: %s", algo, argmax_metrics)

    winner = max(report["models"], key=lambda a: report["models"][a]["test_argmax"]["auc_roc_ovr_macro"])
    pipe, thr = fitted[winner]
    m = report["models"][winner]
    report["winner"] = winner
    report["gates"] = {
        "auc_roc": m["test_argmax"]["auc_roc_ovr_macro"] >= THRESHOLDS["auc_roc"],
        "recall_critical": m["test_argmax"]["recall_critical"] >= THRESHOLDS["recall_critical"],
        "precision_critical": m["test_argmax"]["precision_critical"] >= THRESHOLDS["precision_critical"],
        "cv_variance": m["cv"]["auc_cv_variation"] < THRESHOLDS["cv_variance"],
    }

    # Perfiles de mecanismo más frecuentes (para marginalizar en la API)
    prof = (df[MECHANISM_FEATURES].fillna({"num_units": 2}).value_counts(normalize=True).head(80)
            .rename("weight").reset_index())
    prof["weight"] = prof["weight"] / prof["weight"].sum()

    artifact = {
        "pipeline": pipe,
        "meta": {
            "algorithm": winner,
            "features": FEATURES,
            "classes": SEVERITY_LABELS,
            "critical_threshold_f1": thr,
            "test_metrics": m["test_argmax"],
            "trained_at": report["trained_at"],
            "n_train": int(len(X_train)),
            "mechanism_profiles": prof.to_dict(orient="records"),
            "mechanism_coverage": float(df[MECHANISM_FEATURES].fillna({"num_units": 2}).value_counts(normalize=True)
                                        .head(40).sum()),
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
    }
    t0 = time.perf_counter()
    loaded["pipeline"].predict_proba(X_test.iloc[[0]])
    report["artifact"]["single_inference_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    report["artifact"]["gate_size_lt_100mb"] = report["artifact"]["size_mb"] < 100

    # Riesgo medio predicho por celda de 500 m (capa coroplética del frontend)
    grid = df[["grid_x", "grid_y", "latitude", "longitude"]].copy()
    grid["p_critical"] = pipe.predict_proba(X)[:, CRITICAL]
    grid["observed_critical"] = (y == CRITICAL).astype(float)
    grid = grid.groupby(["grid_x", "grid_y"], as_index=False).agg(
        crashes=("p_critical", "size"), mean_p_critical=("p_critical", "mean"),
        observed_critical_rate=("observed_critical", "mean"), lat=("latitude", "mean"), lon=("longitude", "mean"))
    grid.to_parquet(settings.processed_dir / "gold_grid_ml.parquet", index=False)
    try:
        from app.services.olap.duckdb_engine import attach_ml_grid
        attach_ml_grid(grid)
        report["grid_cells_scored"] = int(len(grid))
    except Exception as exc:  # DuckDB bloqueado o inexistente: no es fatal
        logger.warning("No se pudo adjuntar gold_grid_ml a DuckDB: %s", exc)

    out = settings.processed_dir / "model_report.json"
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    # Copia junto al modelo para que la API exponga las métricas
    Path(model_path).with_name("model_report.json").write_text(json.dumps(report, indent=2, default=str),
                                                               encoding="utf-8")
    logger.info("Ganador: %s | gates: %s | artefacto: %s", winner, report["gates"], report["artifact"])
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Entrenamiento de modelos de riesgo vial")
    parser.add_argument("--input", default=str(settings.processed_dir / "features_gold.parquet"))
    parser.add_argument("--algorithm", default="both", choices=["xgboost", "random_forest", "both"])
    parser.add_argument("--cv-sample", type=int, default=120_000,
                        help="Filas usadas en la búsqueda 5-fold (el modelo final usa todo el train)")
    parser.add_argument("--model-path", default=settings.MODEL_PATH)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    algos = ["xgboost", "random_forest"] if args.algorithm == "both" else [args.algorithm]
    report = train(args.input, algos, args.cv_sample, args.model_path)
    print(json.dumps({"winner": report["winner"], "gates": report["gates"],
                      "test": report["models"][report["winner"]]["test_argmax"],
                      "artifact": report["artifact"]}, indent=2))


if __name__ == "__main__":
    main()
