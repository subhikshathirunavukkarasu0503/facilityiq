"""Unit tests: Open-Meteo Air Quality integration + weather-coupled sim."""

import json
from datetime import datetime, timezone

import numpy as np

from facilityiq.integrations import air_quality as aq
from facilityiq.simulators.devices import DeviceProfile, EnergySimulator, HVACSimulator

START = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_aqi_bands():
    assert aq.aqi_band(10) == "GOOD"
    assert aq.aqi_band(50) == "MODERATE"
    assert aq.aqi_band(95) == "VERY POOR"


def test_ventilation_advice_flips_with_air_quality():
    good = aq.AirQualityReading(5, 10, 30, 200, 15, "live", 0)
    bad = aq.AirQualityReading(120, 180, 60, 900, 90, "live", 0)
    assert "economizer" in aq.ventilation_advice(good).lower()
    assert "recirculate" in aq.ventilation_advice(bad).lower()


def test_live_fetch_parses_api_shape(monkeypatch):
    payload = {"current": {"pm2_5": 22.0, "pm10": 41.0, "ozone": 55.0,
                           "carbon_monoxide": 310.0, "european_aqi": 38.0}}

    class FakeResp:
        def read(self):
            return json.dumps(payload).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(aq, "urlopen", lambda *a, **k: FakeResp())
    r = aq.get_air_quality()
    assert r.source == "live"
    assert r.pm2_5 == 22.0


def test_failure_falls_back_without_raising(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise OSError("down")

    monkeypatch.setattr(aq, "urlopen", boom)
    monkeypatch.setattr(aq, "_CACHE_FILE", tmp_path / "none.json")
    r = aq.get_air_quality()
    assert r.source == "fallback"


def test_ambient_bias_raises_return_temp():
    cold = HVACSimulator(DeviceProfile("d", "z", "healthy", seed=1),
                         ambient_bias_c=0.0)
    hot = HVACSimulator(DeviceProfile("d", "z", "healthy", seed=1),
                        ambient_bias_c=8.0)
    rt_cold = np.mean([m["metrics"]["return_temp_c"]
                       for m in cold.stream(START, 2)])
    rt_hot = np.mean([m["metrics"]["return_temp_c"]
                      for m in hot.stream(START, 2)])
    assert rt_hot > rt_cold + 2.0


def test_ambient_bias_raises_power_draw():
    cold = EnergySimulator(DeviceProfile("m", "z", "healthy", seed=2),
                           ambient_bias_c=0.0)
    hot = EnergySimulator(DeviceProfile("m", "z", "healthy", seed=2),
                          ambient_bias_c=8.0)
    p_cold = np.mean([m["metrics"]["power_kw"] for m in cold.stream(START, 2)])
    p_hot = np.mean([m["metrics"]["power_kw"] for m in hot.stream(START, 2)])
    assert p_hot > p_cold
