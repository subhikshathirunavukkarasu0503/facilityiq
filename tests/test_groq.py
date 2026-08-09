"""Unit tests: Groq provider + Gemini->Groq failover routing."""

import json

from facilityiq.integrations import gemini as gx
from facilityiq.integrations import groq_llm


def test_groq_call_parses_openai_shape(monkeypatch):
    payload = {"choices": [{"message": {"content": "Groq says OK"}}]}

    class FakeResp:
        def read(self):
            return json.dumps(payload).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(groq_llm, "api_key", lambda: "gsk_test")
    monkeypatch.setattr(groq_llm, "urlopen", lambda *a, **k: FakeResp())
    assert groq_llm._call("hi") == "Groq says OK"


def test_missing_groq_key_raises(monkeypatch):
    monkeypatch.setattr(groq_llm, "api_key", lambda: None)
    try:
        groq_llm._call("hi")
        assert False, "should raise"
    except RuntimeError:
        pass


def test_auto_fails_over_gemini_to_groq(monkeypatch, tmp_path):
    monkeypatch.setattr(gx, "_CACHE_DIR", tmp_path)

    def gemini_down(prompt, **k):
        raise RuntimeError("gemini quota")

    monkeypatch.setattr(gx, "_call", gemini_down)
    monkeypatch.setattr(groq_llm, "_call", lambda p, **k: "groq answer")
    text, source = gx.generate("p", cache_key="k", fallback="fb",
                               provider="auto")
    assert (text, source) == ("groq answer", "groq")


def test_explicit_groq_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(gx, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(groq_llm, "_call", lambda p, **k: "groq only")
    text, source = gx.generate("p", provider="groq")
    assert (text, source) == ("groq only", "groq")


def test_both_down_falls_back_to_template(monkeypatch, tmp_path):
    monkeypatch.setattr(gx, "_CACHE_DIR", tmp_path)

    def down(prompt, **k):
        raise RuntimeError("down")

    monkeypatch.setattr(gx, "_call", down)
    monkeypatch.setattr(groq_llm, "_call", down)
    text, source = gx.generate("p", fallback="template text", provider="auto")
    assert (text, source) == ("template text", "template")


def test_cache_is_per_provider(monkeypatch, tmp_path):
    monkeypatch.setattr(gx, "_CACHE_DIR", tmp_path)
    monkeypatch.setattr(gx, "_call", lambda p, **k: "gemini text")
    monkeypatch.setattr(groq_llm, "_call", lambda p, **k: "groq text")
    t1, _ = gx.generate("p", cache_key="same", provider="gemini")
    t2, _ = gx.generate("p", cache_key="same", provider="groq")
    assert t1 == "gemini text" and t2 == "groq text"
