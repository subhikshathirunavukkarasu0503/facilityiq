"""Feature engineering: raw telemetry -> model-ready feature windows.

Each feature row summarizes one device over a trailing window (default 24h):
rolling means, stds, and linear-trend slopes of the key metrics. Slopes are
the workhorse — degradation is a *direction*, not a level.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

LAKE = Path(__file__).resolve().parents[3] / "data" / "lake"

HVAC_METRICS = [
    "compressor_efficiency", "vibration_mm_s", "filter_dp_pa",
    "motor_temp_c", "supply_temp_c", "return_temp_c",
]
ENERGY_METRICS = ["power_kw", "voltage_v", "power_factor", "thd_pct"]


def load_domain(domain: str, lake: Path | str = LAKE) -> pd.DataFrame:
    """Load all telemetry for one domain from the JSONL lake."""
    rows = []
    root = Path(lake) / domain
    if not root.exists():
        return pd.DataFrame()
    for path in sorted(root.rglob("*.jsonl")):
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                row = {"device_id": rec["device_id"], "zone": rec["zone"],
                       "timestamp": rec["timestamp"], **rec["metrics"]}
                rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")
    return df.sort_values(["device_id", "timestamp"]).reset_index(drop=True)


def _slope(values: np.ndarray) -> float:
    """Least-squares slope per step; 0 for constant/short series."""
    n = len(values)
    if n < 3:
        return 0.0
    x = np.arange(n, dtype=float)
    x -= x.mean()
    denom = float((x**2).sum())
    if denom == 0:
        return 0.0
    return float((x * (values - values.mean())).sum() / denom)


def window_features(df: pd.DataFrame, metrics: list[str],
                    window: str = "24h", step: str = "6h") -> pd.DataFrame:
    """Slide a window over each device's series; one feature row per step.

    Adds `delta_t_c` (supply-return differential) for HVAC when present.
    """
    if df.empty:
        return pd.DataFrame()
    df = df.copy()
    if {"supply_temp_c", "return_temp_c"} <= set(df.columns):
        df["delta_t_c"] = df["return_temp_c"] - df["supply_temp_c"]
        metrics = metrics + ["delta_t_c"]

    out = []
    win = pd.Timedelta(window)
    stp = pd.Timedelta(step)
    for device_id, g in df.groupby("device_id"):
        g = g.set_index("timestamp").sort_index()
        t = g.index.min() + win
        while t <= g.index.max():
            w = g.loc[t - win : t]
            if len(w) >= 8:
                row: dict = {"device_id": device_id, "window_end": t}
                for m in metrics:
                    if m not in w.columns:
                        continue
                    vals = w[m].to_numpy(dtype=float)
                    row[f"{m}_mean"] = vals.mean()
                    row[f"{m}_std"] = vals.std()
                    row[f"{m}_slope"] = _slope(vals)
                    row[f"{m}_last"] = vals[-1]
                out.append(row)
            t += stp
    return pd.DataFrame(out)


def feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in ("device_id", "window_end", "label")]
