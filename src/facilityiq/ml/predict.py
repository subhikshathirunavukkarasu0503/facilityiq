"""Prediction service: score live lake telemetry with the trained models.

Used by the portal. Produces per-device health assessments:
    failure_probability, days_to_maintenance estimate, health status,
    anomaly flags with timestamps.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .features import (
    ENERGY_METRICS, HVAC_METRICS, load_domain, window_features,
)

MODELS_DIR = Path(__file__).resolve().parents[3] / "models"

STATUS_THRESHOLDS = (0.35, 0.65)  # green below, red above


def _load(name: str):
    bundle = joblib.load(MODELS_DIR / f"{name}.joblib")
    return bundle["model"], bundle["features"]


def _status(prob: float) -> str:
    lo, hi = STATUS_THRESHOLDS
    return "green" if prob < lo else ("yellow" if prob < hi else "red")


def _days_to_maintenance(prob: float) -> float:
    """Heuristic mapping: p=0.5 -> ~14 days, p>=0.95 -> immediate."""
    return round(float(max((1.0 - prob) * 28.0, 0.0)), 1)


def score_hvac(lake: Path | str | None = None) -> list[dict]:
    df = load_domain("hvac", lake) if lake else load_domain("hvac")
    if df.empty:
        return []
    feats = window_features(df, HVAC_METRICS)
    if feats.empty:
        return []
    comp_model, comp_cols = _load("hvac_compressor_failure")
    motor_model, motor_cols = _load("motor_degradation")

    out = []
    for device_id, g in feats.groupby("device_id"):
        latest = g.sort_values("window_end").iloc[-1]
        comp_p = float(comp_model.predict_proba(
            latest[comp_cols].to_numpy(dtype=float).reshape(1, -1))[0, 1])
        motor_p = float(motor_model.predict_proba(
            latest[motor_cols].to_numpy(dtype=float).reshape(1, -1))[0, 1])
        prob = max(comp_p, motor_p)
        out.append({
            "device_id": device_id,
            "domain": "hvac",
            "compressor_failure_prob": round(comp_p, 4),
            "motor_degradation_prob": round(motor_p, 4),
            "failure_probability": round(prob, 4),
            "status": _status(prob),
            "days_to_maintenance": _days_to_maintenance(prob),
            "window_end": latest["window_end"].isoformat(),
        })
    return out


def score_energy(lake: Path | str | None = None) -> list[dict]:
    df = load_domain("energy", lake) if lake else load_domain("energy")
    if df.empty:
        return []
    feats = window_features(df, ENERGY_METRICS)
    if feats.empty:
        return []
    model, cols = _load("electrical_fault_detection")

    out = []
    for device_id, g in feats.groupby("device_id"):
        g = g.sort_values("window_end")
        X = g[cols].to_numpy(dtype=float)
        flags = model.predict(X) == -1
        scores = -model.score_samples(X)
        # normalize score to 0..1 within observed range for display
        s = scores[-1]
        prob = float(np.clip((s - scores.min()) /
                             max(scores.max() - scores.min(), 1e-9), 0, 1))
        recent_anoms = [
            {"window_end": we.isoformat(), "score": round(float(sc), 3)}
            for we, sc, fl in zip(g["window_end"], scores, flags) if fl
        ][-10:]
        prob = prob if flags[-1] else min(prob, 0.3)
        out.append({
            "device_id": device_id,
            "domain": "energy",
            "failure_probability": round(prob, 4),
            "status": _status(prob),
            "days_to_maintenance": _days_to_maintenance(prob),
            "anomalies": recent_anoms,
            "anomaly_now": bool(flags[-1]),
            "window_end": g["window_end"].iloc[-1].isoformat(),
        })
    return out


def score_occupancy(lake: Path | str | None = None) -> list[dict]:
    """Utilization analytics (no failure model — descriptive metrics)."""
    df = load_domain("occupancy", lake) if lake else load_domain("occupancy")
    if df.empty:
        return []
    out = []
    for device_id, g in df.groupby("device_id"):
        work = g[(g["timestamp"].dt.weekday < 5) & g["timestamp"].dt.hour.between(8, 18)]
        if work.empty:
            continue
        desk_util = float((work["desk_occupied"] / work["desk_total"]).mean())
        booked = work[work["room_booked"] > 0]
        ghost = float((1 - booked["room_occupied"]).mean()) if len(booked) else 0.0
        out.append({
            "device_id": device_id,
            "domain": "occupancy",
            "zone": g["zone"].iloc[0],
            "avg_desk_utilization": round(desk_util, 3),
            "ghost_booking_rate": round(ghost, 3),
            "peak_occupancy": float(work["occupancy_count"].max()),
            "status": "green",
            "failure_probability": 0.0,
        })
    return out


def fleet_assessment(lake: Path | str | None = None) -> dict:
    """Full portal payload: all domains scored + fleet-level rollup."""
    hvac = score_hvac(lake)
    energy = score_energy(lake)
    occ = score_occupancy(lake)
    assets = hvac + energy
    counts = {"green": 0, "yellow": 0, "red": 0}
    for a in assets:
        counts[a["status"]] += 1
    return {
        "hvac": hvac, "energy": energy, "occupancy": occ,
        "fleet": {
            "total_assets": len(assets),
            "status_counts": counts,
            "active_alerts": [a for a in assets if a["status"] != "green"],
        },
    }


def explain_prediction(assessment: dict) -> str:
    """Template-based natural-language explanation of one asset's prediction.

    Mid-term scope: deterministic templates (doc's documented fallback).
    Gemini narrative generation replaces this post-mid-term.
    """
    p = assessment["failure_probability"]
    dev = assessment["device_id"]
    if assessment["status"] == "green":
        return (f"{dev} is operating normally (failure probability "
                f"{p:.0%}). No action needed; next review at the regular cycle.")
    drivers = []
    if assessment.get("compressor_failure_prob", 0) >= 0.5:
        drivers.append("compressor efficiency degradation and shrinking "
                       "supply/return temperature differential")
    if assessment.get("motor_degradation_prob", 0) >= 0.5:
        drivers.append("rising vibration amplitude and motor temperature trend")
    if assessment.get("anomaly_now"):
        drivers.append("anomalous power-quality pattern (voltage sags / "
                       "harmonic distortion)")
    driver_txt = "; ".join(drivers) if drivers else "multiple degradation signals"
    return (
        f"{dev} shows {p:.0%} probability of failure within the prediction "
        f"horizon, driven by {driver_txt}. Recommended: schedule inspection "
        f"within {assessment['days_to_maintenance']:.0f} days."
    )


def save_assessment(path: Path | str, lake: Path | str | None = None) -> dict:
    result = fleet_assessment(lake)
    Path(path).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result
