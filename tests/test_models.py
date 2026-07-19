"""Model quality tests: train on small datasets and assert accuracy floors,
plus end-to-end pipeline integration (simulate -> lake -> features -> score).

These are the mid-term "model accuracy tests (precision, recall, F1, ROC-AUC)"
from the QA plan. Full-size training happens via `python -m facilityiq.ml.train_all`;
here we verify the pipeline produces models above the accuracy bar.
"""

import json

import pytest

from facilityiq.ml import train_all
from facilityiq.ml.datasets import build_energy_dataset, build_hvac_dataset


@pytest.fixture(scope="module")
def hvac_metrics():
    return train_all.train_hvac()


@pytest.fixture(scope="module")
def electrical_metrics():
    return train_all.train_electrical()


@pytest.fixture(scope="module")
def motor_metrics():
    return train_all.train_motor()


def test_hvac_dataset_is_labeled_and_balanced_enough():
    df = build_hvac_dataset()
    assert {"label", "device_id", "window_end"} <= set(df.columns)
    pos = df["label"].mean()
    assert 0.02 < pos < 0.8, f"positive rate {pos} implausible"


def test_energy_dataset_has_anomaly_labels():
    df = build_energy_dataset()
    assert df["label"].sum() > 0
    assert (df["label"] == 0).sum() > 0


def test_hvac_model_meets_accuracy_bar(hvac_metrics):
    assert hvac_metrics["f1"] >= 0.85, hvac_metrics
    assert hvac_metrics["roc_auc"] >= 0.90, hvac_metrics


def test_motor_model_meets_accuracy_bar(motor_metrics):
    assert motor_metrics["f1"] >= 0.85, motor_metrics


def test_electrical_anomaly_detection_recall(electrical_metrics):
    # QA plan: >90% anomaly detection (true positive rate)
    assert electrical_metrics["recall"] >= 0.90, electrical_metrics


def test_metrics_files_written(hvac_metrics):
    path = train_all.MODELS_DIR / "hvac_compressor_failure_metrics.json"
    assert path.exists()
    stored = json.loads(path.read_text())
    assert stored["f1"] == hvac_metrics["f1"]


def test_end_to_end_scoring(tmp_path, hvac_metrics, electrical_metrics):
    """Simulate fresh fleet -> lake -> feature windows -> model scores.

    Faulty devices must score worse than healthy ones."""
    from facilityiq.ingestion.sinks import LocalLakeSink
    from facilityiq.ml.predict import fleet_assessment
    from facilityiq.simulators.devices import simulate_fleet

    sink = LocalLakeSink(tmp_path)
    for msg in simulate_fleet(days=3.0):
        sink.write(msg)

    result = fleet_assessment(tmp_path)
    assert result["fleet"]["total_assets"] > 0
    assessments = {a["device_id"]: a for a in result["hvac"]}
    assert assessments["hvac-pump-01"]["failure_probability"] >= 0.5, (
        "steady-state faulty pump must score as at-risk, got "
        f"{assessments['hvac-pump-01']}")
    assert assessments["hvac-pump-01"]["status"] != "green"
    assert assessments["hvac-ahu-01"]["failure_probability"] < 0.35, (
        "healthy AHU must score low")
    assert result["occupancy"], "occupancy analytics must be present"
