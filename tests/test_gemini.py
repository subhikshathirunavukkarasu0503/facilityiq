"""Unit tests: Gemini integration — fallback chain, caching, env loading.

No network calls in CI: _call is monkeypatched. One optional live smoke test
runs only when GEMINI_API_KEY is present locally.
"""

import os

import pytest

from facilityiq.integrations import gemini as gx


def test_generate_falls_back_to_template_on_error(monkeypatch):
    monkeypatch.setattr(gx, "_call", lambda p, **k: (_ for _ in ()).throw(
        RuntimeError("quota")))
    text, source = gx.generate("prompt", cache_key=None,
                               fallback="template text")
    assert source == "template"
    assert text == "template text"


def test_generate_uses_disk_cache(monkeypatch, tmp_path):
    monkeypatch.setattr(gx, "_CACHE_DIR", tmp_path)
    calls = {"n": 0}

    def fake_call(prompt, **k):
        calls["n"] += 1
        return "generated once"

    monkeypatch.setattr(gx, "_call", fake_call)
    t1, s1 = gx.generate("p", cache_key="k1", fallback="")
    t2, s2 = gx.generate("p", cache_key="k1", fallback="")
    assert (t1, s1) == ("generated once", "gemini")
    assert (t2, s2) == ("generated once", "cache")
    assert calls["n"] == 1


def test_asset_narrative_prompt_carries_data(monkeypatch, tmp_path):
    monkeypatch.setattr(gx, "_CACHE_DIR", tmp_path)
    captured = {}

    def fake_call(prompt, **k):
        captured["prompt"] = prompt
        return "explanation"

    monkeypatch.setattr(gx, "_call", fake_call)
    assessment = {"device_id": "hvac-x", "failure_probability": 0.9,
                  "status": "red", "domain": "hvac"}
    text, source = gx.asset_narrative(assessment, fallback="fb")
    assert source == "gemini"
    assert "hvac-x" in captured["prompt"]
    assert "0.9" in captured["prompt"]


def test_missing_key_raises_then_falls_back(monkeypatch):
    monkeypatch.setattr(gx, "api_key", lambda: None)
    text, source = gx.generate("p", fallback="fb")
    assert source == "template"


@pytest.mark.skipif(not gx.api_key(), reason="no GEMINI_API_KEY configured")
def test_live_gemini_smoke():
    text = gx._call("Reply with exactly: OK")
    assert "OK" in text
