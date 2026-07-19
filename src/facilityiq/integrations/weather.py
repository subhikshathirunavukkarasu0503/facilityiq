"""Live external data: Open-Meteo weather API (free, no API key).

Outdoor conditions drive real HVAC load, so the portal enriches equipment
status with live site weather and a derived cooling-load index. Network
failures degrade gracefully to a cached/fallback reading — the portal never
breaks because an external API is down (RFP risk #4 mitigation pattern).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.request import urlopen

# Psiog Digital HQ — Chennai, IN
DEFAULT_LAT, DEFAULT_LON = 13.0827, 80.2707

API_URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude={lat}&longitude={lon}"
    "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
    "weather_code,wind_speed_10m"
    "&hourly=temperature_2m&forecast_days=1&timezone=auto"
)

_CACHE_FILE = Path(__file__).resolve().parents[3] / "data" / "weather_cache.json"
_CACHE_TTL_S = 15 * 60

WMO_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog", 51: "Light drizzle", 53: "Drizzle",
    55: "Dense drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Rain showers", 81: "Rain showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm w/ hail", 99: "Thunderstorm w/ hail",
}


@dataclass
class WeatherReading:
    temperature_c: float
    humidity_pct: float
    feels_like_c: float
    wind_kmh: float
    condition: str
    hourly_temps: list[float]
    source: str  # 'live' | 'cache' | 'fallback'
    fetched_at: float


def cooling_load_index(temp_c: float, humidity_pct: float) -> float:
    """0..1 index of how hard HVAC must work for indoor 24C setpoint.

    Simple sensible+latent proxy: temperature excess over setpoint plus a
    humidity penalty, normalized to a 24-45C / 30-95%RH envelope.
    """
    sensible = max(temp_c - 24.0, 0.0) / 21.0
    latent = max(humidity_pct - 30.0, 0.0) / 65.0 * 0.4
    return round(min(sensible + latent, 1.0), 3)


def _fetch_live(lat: float, lon: float, timeout: float) -> WeatherReading:
    with urlopen(API_URL.format(lat=lat, lon=lon), timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    cur = data["current"]
    return WeatherReading(
        temperature_c=float(cur["temperature_2m"]),
        humidity_pct=float(cur["relative_humidity_2m"]),
        feels_like_c=float(cur["apparent_temperature"]),
        wind_kmh=float(cur["wind_speed_10m"]),
        condition=WMO_CODES.get(int(cur["weather_code"]), "Unknown"),
        hourly_temps=[float(t) for t in data["hourly"]["temperature_2m"]],
        source="live",
        fetched_at=time.time(),
    )


def get_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON,
                timeout: float = 6.0) -> WeatherReading:
    """Live reading, else disk cache, else static fallback. Never raises."""
    try:
        reading = _fetch_live(lat, lon, timeout)
        try:
            _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_text(json.dumps(asdict(reading)), encoding="utf-8")
        except OSError:
            pass
        return reading
    except Exception:
        pass

    try:
        cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        cached["source"] = "cache"
        return WeatherReading(**cached)
    except Exception:
        pass

    return WeatherReading(
        temperature_c=32.0, humidity_pct=70.0, feels_like_c=37.0,
        wind_kmh=12.0, condition="Unavailable (offline fallback)",
        hourly_temps=[30 + i % 5 for i in range(24)],
        source="fallback", fetched_at=time.time(),
    )
