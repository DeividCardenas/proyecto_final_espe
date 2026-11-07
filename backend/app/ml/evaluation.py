"""Utilidades de validación comunes a los modelos de riesgo (Fase 3).

Todo lo que decide algo sobre el modelo (umbral, hiperparámetros, ganador) se
calcula con datos de **validación** o predicciones **fuera de pliegue**; el
conjunto de prueba sólo se usa una vez, para reportar.
"""
from __future__ import annotations

import hashlib
import platform
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, precision_recall_curve


# ------------------------------------------------------------------------------
# Particiones
# ------------------------------------------------------------------------------
def temporal_masks(dates: pd.Series, test_months: int, val_months: int) -> tuple[pd.Series, pd.Series, pd.Series, dict]:
    """Divide por fecha: train < val_start <= val < test_start <= test.

    El test son los últimos ``test_months`` meses de datos y la validación los
    ``val_months`` meses inmediatamente anteriores.
    """
    d = pd.to_datetime(dates)
    end = d.max().normalize() + pd.Timedelta(days=1)
    test_start = end - pd.DateOffset(months=test_months)
    val_start = test_start - pd.DateOffset(months=val_months)
    train = d < val_start
    val = (d >= val_start) & (d < test_start)
    test = d >= test_start
    if not train.any() or not val.any() or not test.any():
        raise ValueError(f"Datos insuficientes para la partición temporal ({d.min()} -> {d.max()}): "
                         f"train < {val_start.date()} <= val < {test_start.date()} <= test")
    cut = {"train": f"{d.min().date()} -> {val_start.date()}", "val": f"{val_start.date()} -> {test_start.date()}",
           "test": f"{test_start.date()} -> {end.date()}"}
    return train, val, test, cut


def spatial_blocks(grid_x: pd.Series, grid_y: pd.Series, cells: int = 4) -> pd.Series:
    """Bloques de ``cells`` x ``cells`` celdas de 500 m (~2 km) para GroupKFold."""
    return ((grid_x // cells).astype(int).astype(str) + "_" + (grid_y // cells).astype(int).astype(str))


# ------------------------------------------------------------------------------
# Umbrales de decisión (se eligen en validación, nunca en test)
# ------------------------------------------------------------------------------
def f1_threshold(y_pos: np.ndarray, score: np.ndarray) -> float:
    prec, rec, thr = precision_recall_curve(y_pos, score)
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    return float(thr[int(np.nanargmax(f1[:-1]))])


def recall_threshold(y_pos: np.ndarray, score: np.ndarray, target: float) -> float:
    """Umbral más alto (más preciso) que aún logra ``recall >= target``."""
    prec, rec, thr = precision_recall_curve(y_pos, score)
    ok = np.where(rec[:-1] >= target)[0]
    return float(thr[ok[-1]]) if len(ok) else float(thr[0])


def decide(proba: np.ndarray, positive: int, threshold: float) -> np.ndarray:
    """Clase ``positive`` si su probabilidad supera el umbral; si no, argmax del resto."""
    rest = proba.copy()
    rest[:, positive] = -np.inf
    return np.where(proba[:, positive] >= threshold, positive, rest.argmax(axis=1))


# ------------------------------------------------------------------------------
# Calibración y métricas para clases raras
# ------------------------------------------------------------------------------
def calibration(y_pos: np.ndarray, p: np.ndarray, bins: int = 10) -> dict:
    """Brier, ECE y curva de fiabilidad por cuantiles de la probabilidad predicha."""
    y_pos = np.asarray(y_pos, dtype=float)
    p = np.asarray(p, dtype=float)
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)))
    idx = np.clip(np.searchsorted(edges, p, side="right") - 1, 0, max(len(edges) - 2, 0))
    curve, ece = [], 0.0
    for b in range(max(len(edges) - 1, 1)):
        m = idx == b
        if not m.any():
            continue
        mp, mo = float(p[m].mean()), float(y_pos[m].mean())
        ece += m.mean() * abs(mp - mo)
        curve.append({"mean_predicted": round(mp, 5), "observed_rate": round(mo, 5), "n": int(m.sum())})
    return {
        "brier": float(brier_score_loss(y_pos, p)),
        "ece": float(ece),
        "mean_predicted": float(p.mean()),
        "observed_rate": float(y_pos.mean()),
        "reliability": curve,
    }


def rare_class_metrics(y_pos: np.ndarray, p: np.ndarray, pred_pos: np.ndarray) -> dict:
    base = float(np.mean(y_pos))
    tp = float(np.sum(pred_pos & y_pos))
    precision = tp / max(float(np.sum(pred_pos)), 1.0)
    return {
        "average_precision": float(average_precision_score(y_pos, p)),
        "base_rate": base,
        "lift": precision / base if base else 0.0,
    }


# ------------------------------------------------------------------------------
# Priorización (captura en el top-k %) e intervalos bootstrap
# ------------------------------------------------------------------------------
def top_share_capture(score: np.ndarray, events: np.ndarray, share: float = 0.10) -> float:
    n_top = max(1, int(len(score) * share))
    order = np.argsort(-score, kind="stable")
    total = events.sum()
    return float(events[order[:n_top]].sum() / total) if total else 0.0


def bootstrap_capture(scores: dict[str, np.ndarray], events: np.ndarray, share: float = 0.10,
                      reps: int = 500, seed: int = 42) -> dict:
    """IC 95 % de la captura top-k por remuestreo de unidades (pareado entre modelos).

    Se usa el mismo remuestreo para todos los puntajes, así las diferencias entre
    ellos también tienen intervalo (``diff_vs``).
    """
    rng = np.random.default_rng(seed)
    n = len(events)
    draws = {k: np.empty(reps) for k in scores}
    for r in range(reps):
        idx = rng.integers(0, n, n)
        ev = events[idx]
        for k, s in scores.items():
            draws[k][r] = top_share_capture(s[idx], ev, share)
    out = {}
    for k, v in draws.items():
        out[k] = {"capture": top_share_capture(scores[k], events, share),
                  "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))],
                  "se": float(v.std(ddof=1))}
    out["_draws"] = draws
    return out


def paired_diff(boot: dict, a: str, b: str) -> dict:
    d = boot["_draws"][a] - boot["_draws"][b]
    return {"mean": float(boot[a]["capture"] - boot[b]["capture"]),
            "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "significant": bool(np.percentile(d, 2.5) > 0 or np.percentile(d, 97.5) < 0)}


# ------------------------------------------------------------------------------
# Reproducibilidad
# ------------------------------------------------------------------------------
def provenance(data: pd.DataFrame | None = None, input_path: str | None = None) -> dict:
    """Commit, versiones de librerías y huella de los datos de entrenamiento."""
    import joblib
    import sklearn
    import xgboost

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
                                cwd=Path(__file__).resolve().parent).stdout.strip() or None
    except Exception:  # git no disponible en el contenedor
        commit = None
    info: dict = {
        "git_commit": commit,
        "python": platform.python_version(),
        "versions": {"scikit-learn": sklearn.__version__, "xgboost": xgboost.__version__,
                     "pandas": pd.__version__, "numpy": np.__version__, "joblib": joblib.__version__},
    }
    if input_path and Path(input_path).exists():
        h = hashlib.sha256()
        with open(input_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        info["input"] = {"path": str(input_path), "sha256": h.hexdigest()}
    if data is not None:
        info["data_fingerprint"] = hashlib.sha256(
            pd.util.hash_pandas_object(data, index=False).to_numpy().tobytes()).hexdigest()
        info["n_rows"] = int(len(data))
    return info
