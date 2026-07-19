"""Live occupancy data: City of Melbourne pedestrian counting system.

Real, physical footfall sensors operated by the City of Melbourne, published
minute-by-minute (last hour) on their open data portal — free, no API key.
The portal maps these to 'zones' alongside the simulated office occupancy so
the space-utilization analytics run against genuinely live sensor data.

Same never-raise fallback chain as the other integrations.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.request import urlopen

API_URL = (
    "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/"
    "pedestrian-counting-system-past-hour-counts-per-minute/records"
    "?limit=100&order_by=sensing_datetime%20desc"
)

_CACHE_FILE = Path(__file__).resolve().parents[3] / "data" / "footfall_cache.json"


@dataclass
class FootfallReading:
    # location_id -> {"total": int, "latest_minute": str, "samples": int}
    locations: dict
    latest_datetime: str
    source: str  # 'live' | 'cache' | 'fallback'
    fetched_at: float


def get_footfall(timeout: float = 8.0) -> FootfallReading:
    """Aggregate the most recent minute-level counts per sensor location."""
    try:
        with urlopen(API_URL, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        locs: dict = {}
        latest = ""
        for rec in data.get("results", []):
            lid = str(rec["location_id"])
            entry = locs.setdefault(lid, {"total": 0, "latest_minute": "",
                                          "samples": 0})
            entry["total"] += int(rec["total_of_directions"] or 0)
            entry["samples"] += 1
            ts = rec["sensing_datetime"]
            entry["latest_minute"] = max(entry["latest_minute"], ts)
            latest = max(latest, ts)
        if not locs:
            raise ValueError("no records")
        reading = FootfallReading(locations=locs, latest_datetime=latest,
                                  source="live", fetched_at=time.time())
        try:
            _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_text(json.dumps(asdict(reading)),
                                   encoding="utf-8")
        except OSError:
            pass
        return reading
    except Exception:
        pass
    try:
        cached = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        cached["source"] = "cache"
        return FootfallReading(**cached)
    except Exception:
        pass
    return FootfallReading(
        locations={"demo-1": {"total": 120, "latest_minute": "", "samples": 60}},
        latest_datetime="", source="fallback", fetched_at=time.time())


def busiest(reading: FootfallReading, n: int = 5) -> list[tuple[str, int]]:
    """Top-n sensor locations by pedestrian volume in the covered window."""
    ranked = sorted(reading.locations.items(),
                    key=lambda kv: -kv[1]["total"])
    return [(lid, info["total"]) for lid, info in ranked[:n]]
