"""Gemini narrative generation: ML outputs -> plain-language guidance.

Uses the REST API directly (no SDK dependency). Model pinned to the
`gemini-flash-latest` alias so Google-side retirements don't break the app.

Fallback chain mirrors the weather integration: live call -> disk cache ->
deterministic template (facilityiq.ml.predict.explain_prediction). The portal
therefore always renders, with or without network/quota — RFP risk #4.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = "gemini-flash-latest"
API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent")

_ROOT = Path(__file__).resolve().parents[3]
_CACHE_DIR = _ROOT / "data" / "gemini_cache"

SYSTEM_STYLE = (
    "You are FacilityIQ, an assistant for facility maintenance teams. "
    "Write for a facilities manager: concrete, specific, no fluff, "
    "no markdown headers. Never invent numbers not present in the data."
)


def _load_env() -> None:
    """Populate os.environ from the project .env (no python-dotenv dep)."""
    env = _ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def api_key() -> str | None:
    _load_env()
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    try:  # Streamlit Cloud stores secrets in st.secrets, not the environment
        import streamlit as st

        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def _call(prompt: str, timeout: float = 25.0) -> str:
    key = api_key()
    if not key:
        raise RuntimeError("GEMINI_API_KEY not set")
    body = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_STYLE}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2500},
    }).encode()
    req = Request(API_URL, data=body, headers={
        "Content-Type": "application/json", "x-goog-api-key": key})
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    parts = data["candidates"][0]["content"]["parts"]
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise RuntimeError("empty Gemini response")
    return text


def generate(prompt: str, cache_key: str | None = None,
             fallback: str = "") -> tuple[str, str]:
    """Return (text, source) with source in {'gemini', 'cache', 'template'}.

    cache_key: stable id for disk-caching (e.g. device + probability bucket) so
    repeated portal reruns don't burn quota; None disables caching.
    """
    path = None
    if cache_key:
        digest = hashlib.sha256(cache_key.encode()).hexdigest()[:24]
        path = _CACHE_DIR / f"{digest}.txt"
        if path.exists():
            return path.read_text(encoding="utf-8"), "cache"
    try:
        text = _call(prompt)
        if path:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return text, "gemini"
    except Exception:
        return fallback, "template"


def asset_narrative(assessment: dict, weather: dict | None = None,
                    fallback: str = "") -> tuple[str, str]:
    """Explain one asset's prediction in plain language."""
    ctx = {k: v for k, v in assessment.items() if k != "anomalies"}
    if assessment.get("anomalies"):
        ctx["recent_anomaly_count"] = len(assessment["anomalies"])
    prompt = (
        "Explain this equipment health prediction to the facilities team in "
        "3-4 sentences: what the ML models see, why it matters, and the "
        "single most important next action.\n\n"
        f"Prediction data (JSON):\n{json.dumps(ctx, default=str)}\n"
    )
    if weather:
        prompt += (f"\nCurrent site conditions: {json.dumps(weather)} "
                   "(mention only if relevant to HVAC stress).")
    bucket = round(assessment.get("failure_probability", 0) * 20) / 20
    key = f"asset:{assessment['device_id']}:{bucket}:{MODEL}"
    return generate(prompt, cache_key=key, fallback=fallback)


def weekly_summary(fleet_data: dict, fallback: str = "") -> tuple[str, str]:
    """Fleet-wide facility health summary for the weekly report."""
    slim = {
        "fleet": fleet_data["fleet"]["status_counts"],
        "alerts": [
            {"device": a["device_id"], "domain": a["domain"],
             "failure_probability": a["failure_probability"],
             "days_to_maintenance": a["days_to_maintenance"]}
            for a in fleet_data["fleet"]["active_alerts"]
        ],
        "occupancy": [
            {"zone": o.get("zone"), "desk_utilization": o["avg_desk_utilization"],
             "ghost_booking_rate": o["ghost_booking_rate"]}
            for o in fleet_data.get("occupancy", [])
        ],
    }
    prompt = (
        "Write a weekly facility health summary (5-7 sentences, one "
        "paragraph per theme: equipment risk, energy, space utilization). "
        "End with the top 3 priority actions as a numbered list.\n\n"
        f"This week's data (JSON):\n{json.dumps(slim, default=str)}"
    )
    key = "weekly:" + hashlib.sha256(
        json.dumps(slim, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return generate(prompt, cache_key=key, fallback=fallback)
