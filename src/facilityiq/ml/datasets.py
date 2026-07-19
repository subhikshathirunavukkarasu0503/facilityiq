"""Build labeled training datasets from dedicated training simulations.

Training data is generated from a large simulated fleet (not the live POC
fleet) so models never memorize the demo devices. Labels come from the
simulator's ground-truth degradation profile:

- Failure prediction (HVAC / motor): a window is positive if the device fails
  within the prediction horizon after the window ends.
- Electrical fault: windows on faulty/late-degrading meters are anomalies —
  labels used for *evaluation only* (Isolation Forest trains unsupervised).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from ..simulators.devices import (
    DeviceProfile, HVACSimulator, EnergySimulator,
)
from .features import window_features, HVAC_METRICS, ENERGY_METRICS

HORIZON_DAYS = 7.0
SPAN_DAYS = 28.0


def _training_hvac_fleet(n_per_class: int = 12) -> list[DeviceProfile]:
    fleet = []
    for i in range(n_per_class):
        fleet.append(DeviceProfile(f"train-hvac-h{i}", "z", "healthy", seed=100 + i))
        fleet.append(DeviceProfile(
            f"train-hvac-d{i}", "z", "degrading",
            failure_at=0.5 + 0.5 * (i / max(n_per_class - 1, 1)), seed=200 + i))
    # Steady-state failed equipment: degraded LEVELS with flat slopes, so the
    # model learns absolute condition, not just trend direction.
    for i in range(max(n_per_class // 2, 1)):
        fleet.append(DeviceProfile(f"train-hvac-f{i}", "z", "faulty", seed=700 + i))
    return fleet


def _training_energy_fleet(n_per_class: int = 12) -> list[DeviceProfile]:
    fleet = []
    for i in range(n_per_class):
        fleet.append(DeviceProfile(f"train-nrg-h{i}", "z", "healthy", seed=300 + i))
        fleet.append(DeviceProfile(
            f"train-nrg-f{i}", "z", "faulty" if i % 2 else "degrading",
            failure_at=0.4 + 0.5 * (i / max(n_per_class - 1, 1)), seed=400 + i))
    return fleet


def _simulate(sim_cls, fleet, span_days: float) -> pd.DataFrame:
    start = datetime.now(timezone.utc) - timedelta(days=span_days)
    rows = []
    for profile in fleet:
        sim = sim_cls(profile)
        for msg in sim.stream(start, span_days):
            rows.append({
                "device_id": msg["device_id"], "zone": msg["zone"],
                "timestamp": msg["timestamp"], **msg["metrics"],
            })
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    return df.sort_values(["device_id", "timestamp"]).reset_index(drop=True)


def _label_failure_windows(feats: pd.DataFrame, fleet: list[DeviceProfile],
                           span_days: float, horizon_days: float) -> pd.DataFrame:
    """label=1 if the device's ground-truth failure time falls within
    [window_end, window_end + horizon]."""
    profiles = {p.device_id: p for p in fleet}
    start = feats["window_end"].min() - pd.Timedelta(f"{1}D")  # approximate span start

    def label(row) -> int:
        p = profiles[row["device_id"]]
        if p.condition == "healthy":
            return 0
        if p.condition == "faulty":
            return 1
        span_start = row["window_end"] - pd.Timedelta(days=span_days)
        # crude but consistent: failure time = span_start + failure_at * span
        fail_time = feats[feats.device_id == row["device_id"]]["window_end"].min() \
            - pd.Timedelta("24h") + pd.Timedelta(days=p.failure_at * span_days)
        # Positive when failure is within the horizon OR has already occurred
        # (post-failure steady-degraded state still needs maintenance).
        return int(fail_time <= row["window_end"] + pd.Timedelta(days=horizon_days))

    feats = feats.copy()
    feats["label"] = feats.apply(label, axis=1)
    _ = start
    return feats


def build_hvac_dataset() -> pd.DataFrame:
    fleet = _training_hvac_fleet()
    raw = _simulate(HVACSimulator, fleet, SPAN_DAYS)
    feats = window_features(raw, HVAC_METRICS)
    return _label_failure_windows(feats, fleet, SPAN_DAYS, HORIZON_DAYS)


def build_motor_dataset() -> pd.DataFrame:
    """Motor/pump degradation reuses HVAC physics (vibration + motor temp are
    the motor-health signals) with an independent fleet and seeds."""
    fleet = []
    for i in range(12):
        fleet.append(DeviceProfile(f"train-mot-h{i}", "z", "healthy", seed=500 + i))
        fleet.append(DeviceProfile(
            f"train-mot-d{i}", "z", "degrading",
            failure_at=0.45 + 0.5 * (i / 11), seed=600 + i))
    for i in range(6):
        fleet.append(DeviceProfile(f"train-mot-f{i}", "z", "faulty", seed=800 + i))
    raw = _simulate(HVACSimulator, fleet, SPAN_DAYS)
    feats = window_features(
        raw, ["vibration_mm_s", "motor_temp_c", "compressor_efficiency"])
    return _label_failure_windows(feats, fleet, SPAN_DAYS, HORIZON_DAYS)


def build_energy_dataset() -> pd.DataFrame:
    fleet = _training_energy_fleet()
    raw = _simulate(EnergySimulator, fleet, SPAN_DAYS)
    feats = window_features(raw, ENERGY_METRICS)
    profiles = {p.device_id: p for p in fleet}
    feats = feats.copy()
    # Anomaly ground truth (evaluation only): any non-healthy device window in
    # the back half of its life, or a faulty device anywhere.
    def label(row) -> int:
        p = profiles[row["device_id"]]
        if p.condition == "healthy":
            return 0
        if p.condition == "faulty":
            return 1
        dev = feats[feats.device_id == row["device_id"]]["window_end"]
        frac = (row["window_end"] - dev.min()) / max(dev.max() - dev.min(), pd.Timedelta("1s"))
        return int(frac >= 0.55 * p.failure_at + 0.25)

    feats["label"] = feats.apply(label, axis=1)
    return feats
