"""Live outdoor air quality: Open-Meteo Air Quality API (free, no API key).

Outdoor AQ drives real facility decisions: high PM2.5 means recirculate
indoor air and raise filtration; good outdoor air means economizer mode
(free cooling). The portal shows a live ventilation recommendation.

Same never-raise fallback chain as the weather integration.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.request import urlopen

DEFAULT_LAT, DEFAULT_LON = 13.0827, 80.2707  # Chennai

API_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    "?latitude={lat}&longitude={lon}"
    "&current=pm2_5,pm10,ozone,carbon_monoxide,european_aqi"
    "&timezone=auto"
)

_CACHE_FILE = Path(__file__).resolve().parents[3] / "data" / "aq_cache.json"


@dataclass
class AirQualityReading:
    pm2_5: float          # µg/m³
    pm10: float           # µg/m³
    ozone: float          # µg/m³
    co: float             # µg/m³
    aqi: float            # European AQI (0-20 good … 100+ extremely poor)
    source: str           # 'live' | 'cache' | 'fallback'
    fetched_at: float


def aqi_band(aqi: float) -> str:
    if aqi <= 20:
        return "GOOD"
    if aqi <= 40:
        return "FAIR"
    if aqi <= 60:
        return "MODERATE"
    if aqi <= 80:
        return "POOR"
    return "VERY POOR"


def ventilation_advice(reading: AirQualityReading) -> str:
    """Plain-language HVAC ventilation recommendation from live outdoor AQ."""
    band = aqi_band(reading.aqi)
    if band in ("GOOD", "FAIR"):
        return ("Outdoor air quality is good — economizer/fresh-air mode "
                "recommended where outdoor temperature allows (free cooling, "
                "lower HVAC load).")
    if band == "MODERATE":
        return ("Moderate outdoor air — standard fresh-air ratios are fine; "
                "monitor filter differential pressure.")
    return (f"Outdoor PM2.5 {reading.pm2_5:.0f} µg/m³ ({band}) — minimize "
            "fresh-air intake, recirculate with filtration, and expect faster "
            "filter clogging (watch filter ΔP alerts).")


def get_air_quality(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON,
                    timeout: float = 6.0) -> AirQualityReading:
    """Live reading, else disk cache, else static fallback. Never raises."""
    try:
        with urlopen(API_URL.format(lat=lat, lon=lon), timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        cur = data["current"]
        reading = AirQualityReading(
            pm2_5=float(cur["pm2_5"]), pm10=float(cur["pm10"]),
            ozone=float(cur["ozone"]), co=float(cur["carbon_monoxide"]),
            aqi=float(cur["european_aqi"]), source="live",
            fetched_at=time.time(),
        )
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
        return AirQualityReading(**cached)
    except Exception:
        pass
    return AirQualityReading(pm2_5=35.0, pm10=60.0, ozone=40.0, co=300.0,
                             aqi=45.0, source="fallback",
                             fetched_at=time.time())
