"""Unit tests: feature engineering."""

import numpy as np
import pandas as pd

from facilityiq.ml.features import _slope, feature_columns, window_features


def _toy_frame(n=200, device="dev-1"):
    ts = pd.date_range("2026-06-01", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({
        "device_id": device,
        "zone": "z",
        "timestamp": ts,
        "compressor_efficiency": np.linspace(0.95, 0.55, n),
        "vibration_mm_s": np.linspace(1.0, 8.0, n),
    })


def test_slope_detects_trend():
    assert _slope(np.linspace(0, 10, 20)) > 0
    assert _slope(np.linspace(10, 0, 20)) < 0
    assert _slope(np.full(20, 5.0)) == 0
    assert _slope(np.array([1.0])) == 0


def test_window_features_shape_and_columns():
    feats = window_features(_toy_frame(),
                            ["compressor_efficiency", "vibration_mm_s"])
    assert not feats.empty
    for m in ("compressor_efficiency", "vibration_mm_s"):
        for stat in ("mean", "std", "slope", "last"):
            assert f"{m}_{stat}" in feats.columns


def test_window_features_capture_degradation_direction():
    feats = window_features(_toy_frame(),
                            ["compressor_efficiency", "vibration_mm_s"])
    assert (feats["compressor_efficiency_slope"] < 0).all()
    assert (feats["vibration_mm_s_slope"] > 0).all()


def test_empty_input_gives_empty_output():
    assert window_features(pd.DataFrame(), ["x"]).empty


def test_feature_columns_excludes_meta():
    feats = window_features(_toy_frame(), ["vibration_mm_s"])
    feats["label"] = 0
    cols = feature_columns(feats)
    assert "device_id" not in cols
    assert "window_end" not in cols
    assert "label" not in cols
