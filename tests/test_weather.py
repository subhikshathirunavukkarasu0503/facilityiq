"""Unit tests: Open-Meteo integration — cooling-load model and the
never-raise fallback chain (live -> cache -> static)."""

import json

import pytest

from facilityiq.integrations import weather as wx


def test_cooling_load_bounds():
    assert wx.cooling_load_index(20, 30) == 0.0     # cool + dry: no load
    assert wx.cooling_load_index(50, 100) == 1.0    # extreme: capped
    mid = wx.cooling_load_index(33, 70)
    assert 0.2 < mid < 0.9


def test_cooling_load_monotonic_in_temperature():
    assert wx.cooling_load_index(38, 60) > wx.cooling_load_index(28, 60)


def test_cooling_load_humidity_penalty():
    assert wx.cooling_load_index(30, 90) > wx.cooling_load_index(30, 35)


def test_live_fetch_parses_api_shape(monkeypatch):
    payload = {
        "current": {"temperature_2m": 33.5, "relative_humidity_2m": 68,
                    "apparent_temperature": 39.1, "weather_code": 2,
                    "wind_speed_10m": 14.2},
        "hourly": {"temperature_2m": [30.0] * 24},
    }

    class FakeResp:
        def read(self):
            return json.dumps(payload).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(wx, "urlopen", lambda *a, **k: FakeResp())
    monkeypatch.setattr(wx, "_CACHE_FILE", wx._CACHE_FILE)  # keep path
    r = wx.get_weather()
    assert r.source == "live"
    assert r.temperature_c == 33.5
    assert r.condition == "Partly cloudy"
    assert len(r.hourly_temps) == 24


def test_network_failure_falls_back_without_raising(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(wx, "urlopen", boom)
    monkeypatch.setattr(wx, "_CACHE_FILE", tmp_path / "none.json")
    r = wx.get_weather()
    assert r.source == "fallback"
    assert r.temperature_c > 0  # usable values regardless


def test_cache_used_when_live_fails(monkeypatch, tmp_path):
    cache = tmp_path / "weather_cache.json"
    cache.write_text(json.dumps({
        "temperature_c": 31.0, "humidity_pct": 60.0, "feels_like_c": 35.0,
        "wind_kmh": 10.0, "condition": "Clear sky",
        "hourly_temps": [30.0], "source": "live", "fetched_at": 0.0,
    }))

    def boom(*a, **k):
        raise OSError("down")

    monkeypatch.setattr(wx, "urlopen", boom)
    monkeypatch.setattr(wx, "_CACHE_FILE", cache)
    r = wx.get_weather()
    assert r.source == "cache"
    assert r.temperature_c == 31.0
