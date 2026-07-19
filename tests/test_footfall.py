"""Unit tests: City of Melbourne footfall integration."""

import json

from facilityiq.integrations import melbourne_footfall as mf


def _payload():
    return {"results": [
        {"location_id": 3, "sensing_datetime": "2026-07-19T10:01:00+00:00",
         "total_of_directions": 8},
        {"location_id": 3, "sensing_datetime": "2026-07-19T10:02:00+00:00",
         "total_of_directions": 5},
        {"location_id": 7, "sensing_datetime": "2026-07-19T10:02:00+00:00",
         "total_of_directions": 30},
    ]}


class FakeResp:
    def __init__(self, payload):
        self._p = payload
    def read(self):
        return json.dumps(self._p).encode()
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def test_live_aggregation(monkeypatch, tmp_path):
    monkeypatch.setattr(mf, "urlopen", lambda *a, **k: FakeResp(_payload()))
    monkeypatch.setattr(mf, "_CACHE_FILE", tmp_path / "c.json")
    r = mf.get_footfall()
    assert r.source == "live"
    assert r.locations["3"]["total"] == 13
    assert r.locations["7"]["total"] == 30
    assert r.latest_datetime.startswith("2026-07-19T10:02")


def test_busiest_ranking(monkeypatch, tmp_path):
    monkeypatch.setattr(mf, "urlopen", lambda *a, **k: FakeResp(_payload()))
    monkeypatch.setattr(mf, "_CACHE_FILE", tmp_path / "c.json")
    top = mf.busiest(mf.get_footfall(), 1)
    assert top == [("7", 30)]


def test_failure_falls_back(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(mf, "urlopen", boom)
    monkeypatch.setattr(mf, "_CACHE_FILE", tmp_path / "none.json")
    r = mf.get_footfall()
    assert r.source == "fallback"
    assert r.locations


def test_empty_results_treated_as_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(mf, "urlopen",
                        lambda *a, **k: FakeResp({"results": []}))
    monkeypatch.setattr(mf, "_CACHE_FILE", tmp_path / "none.json")
    assert mf.get_footfall().source == "fallback"
