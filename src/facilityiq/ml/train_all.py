"""Train all three failure/fault models + the cross-domain anomaly pipeline.

Outputs per model into models/:
    <name>.joblib            trained estimator (+ feature list)
    <name>_metrics.json      precision / recall / F1 / ROC-AUC, confusion matrix
    <name>_confusion.png     confusion-matrix plot (docs/evidence)

Grouped train/test split by device_id — windows from one device never appear
in both sets, so metrics measure generalization to unseen equipment.

MLflow tracking is used when available (local ./mlruns), skipped silently
otherwise so CI stays dependency-light.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import (
    GradientBoostingClassifier, IsolationForest, RandomForestClassifier,
)
from sklearn.metrics import (
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit

from .datasets import build_energy_dataset, build_hvac_dataset, build_motor_dataset
from .features import feature_columns

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"


def _split(df, seed=42):
    cols = feature_columns(df)
    X = df[cols].to_numpy(dtype=float)
    y = df["label"].to_numpy(dtype=int)
    groups = df["device_id"].to_numpy()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=seed)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx], cols


def _evaluate(name: str, y_true, y_pred, y_score) -> dict:
    metrics = {
        "model": name,
        "n_test": int(len(y_true)),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_score)), 4)
        if len(set(y_true)) > 1 else None,
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    return metrics


def _save(name: str, model, cols: list[str], metrics: dict) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": cols}, MODELS_DIR / f"{name}.joblib")
    (MODELS_DIR / f"{name}_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cm = np.array(metrics["confusion_matrix"])
        fig, ax = plt.subplots(figsize=(7, 6))
        ax.imshow(cm, cmap="Blues")
        for (i, j), v in np.ndenumerate(cm):
            ax.text(j, i, str(v), ha="center", va="center", fontsize=22,
                    color="white" if v > cm.max() / 2 else "black")
        ax.set_xticks([0, 1], ["healthy", "failure"], fontsize=14)
        ax.set_yticks([0, 1], ["healthy", "failure"], fontsize=14)
        ax.set_xlabel("predicted", fontsize=14)
        ax.set_ylabel("actual", fontsize=14)
        ax.set_title(name, fontsize=15)
        fig.tight_layout()
        fig.savefig(MODELS_DIR / f"{name}_confusion.png", dpi=160)
        plt.close(fig)
    except Exception:
        pass

    try:
        import mlflow

        mlflow.set_experiment("facilityiq")
        with mlflow.start_run(run_name=name):
            mlflow.log_metrics({k: v for k, v in metrics.items()
                                if isinstance(v, (int, float)) and v is not None})
            mlflow.log_param("model", name)
    except Exception:
        pass


def train_hvac() -> dict:
    df = build_hvac_dataset()
    X_tr, X_te, y_tr, y_te, cols = _split(df)
    model = RandomForestClassifier(
        n_estimators=300, max_depth=8, class_weight="balanced", random_state=42)
    model.fit(X_tr, y_tr)
    score = model.predict_proba(X_te)[:, 1]
    metrics = _evaluate("hvac_compressor_failure", y_te, score >= 0.5, score)
    _save("hvac_compressor_failure", model, cols, metrics)
    return metrics


def train_motor() -> dict:
    df = build_motor_dataset()
    X_tr, X_te, y_tr, y_te, cols = _split(df, seed=7)
    model = GradientBoostingClassifier(
        n_estimators=250, max_depth=3, learning_rate=0.08, random_state=7)
    model.fit(X_tr, y_tr)
    score = model.predict_proba(X_te)[:, 1]
    metrics = _evaluate("motor_degradation", y_te, score >= 0.5, score)
    _save("motor_degradation", model, cols, metrics)
    return metrics


def train_electrical() -> dict:
    """Isolation Forest trained unsupervised on healthy meters only; labeled
    windows used purely for evaluation."""
    df = build_energy_dataset()
    cols = feature_columns(df)
    healthy_devices = [d for d in df.device_id.unique() if "-h" in d]
    train_mask = df.device_id.isin(healthy_devices[: len(healthy_devices) // 2])
    X_train = df.loc[train_mask, cols].to_numpy(dtype=float)
    test = df.loc[~train_mask]
    X_test = test[cols].to_numpy(dtype=float)
    y_test = test["label"].to_numpy(dtype=int)

    model = IsolationForest(n_estimators=300, contamination=0.25, random_state=42)
    model.fit(X_train)
    # score_samples: higher = more normal; invert to anomaly score
    anomaly_score = -model.score_samples(X_test)
    y_pred = (model.predict(X_test) == -1).astype(int)
    metrics = _evaluate("electrical_fault_detection", y_test, y_pred, anomaly_score)
    _save("electrical_fault_detection", model, cols, metrics)
    return metrics


def main() -> None:
    results = [train_hvac(), train_electrical(), train_motor()]
    summary = {m["model"]: {k: m[k] for k in ("precision", "recall", "f1", "roc_auc")}
               for m in results}
    (MODELS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
