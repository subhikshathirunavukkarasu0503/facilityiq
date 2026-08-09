"""Groq LLM integration (L&D approval condition: Groq alongside Gemini).

Groq serves open models (Llama) behind an OpenAI-compatible REST API with a
free tier. FacilityIQ uses it as a second narrative provider next to Gemini —
the portal's AI screen lets the user pick Auto / Gemini / Groq, and Auto
fails over Gemini -> Groq -> cached -> deterministic template.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

MODEL = "llama-3.3-70b-versatile"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

_ROOT = Path(__file__).resolve().parents[3]

SYSTEM_STYLE = (
    "You are FacilityIQ, an assistant for facility maintenance teams. "
    "Write for a facilities manager: concrete, specific, no fluff, "
    "no markdown headers. Never invent numbers not present in the data."
)


def api_key() -> str | None:
    env = _ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith("GROQ_API_KEY="):
                val = line.split("=", 1)[1].strip()
                if val:
                    return val
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    try:  # Streamlit Cloud secrets
        import streamlit as st

        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


def _call(prompt: str, timeout: float = 25.0) -> str:
    key = api_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_STYLE},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 1500,
    }).encode()
    req = Request(API_URL, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    })
    with urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    text = data["choices"][0]["message"]["content"].strip()
    if not text:
        raise RuntimeError("empty Groq response")
    return text
