"""Unified telemetry schema and validation.

Every simulator and every ingestion path (local lake or Azure IoT Hub) speaks
this one message shape, so downstream feature engineering never branches on
device type.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

DOMAINS = ("hvac", "energy", "occupancy")

# Metric name -> (min, max) sanity range per domain. Values outside these
# ranges are physically impossible and indicate a corrupt message, not an
# equipment fault (faults stay inside plausible physics).
METRIC_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "hvac": {
        "supply_temp_c": (-10.0, 60.0),
        "return_temp_c": (-10.0, 60.0),
        "humidity_pct": (0.0, 100.0),
        "compressor_efficiency": (0.0, 1.2),
        "vibration_mm_s": (0.0, 50.0),
        "filter_dp_pa": (0.0, 2000.0),
        "motor_temp_c": (0.0, 150.0),
    },
    "energy": {
        "power_kw": (0.0, 5000.0),
        "voltage_v": (0.0, 500.0),
        "current_a": (0.0, 2000.0),
        "power_factor": (0.0, 1.0),
        "thd_pct": (0.0, 100.0),
    },
    "occupancy": {
        "occupancy_count": (0.0, 1000.0),
        "motion_events": (0.0, 10000.0),
        "desk_occupied": (0.0, 1000.0),
        "desk_total": (1.0, 1000.0),
        "room_booked": (0.0, 1.0),
        "room_occupied": (0.0, 1.0),
    },
}


class SchemaError(ValueError):
    """Raised when a telemetry message violates the unified schema."""


@dataclass
class TelemetryMessage:
    device_id: str
    domain: str
    zone: str
    timestamp: str  # ISO-8601 UTC
    metrics: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()


def validate_message(msg: dict[str, Any]) -> TelemetryMessage:
    """Validate a raw message dict and return a typed TelemetryMessage.

    Raises SchemaError on any structural or range violation.
    """
    required = {"device_id", "domain", "zone", "timestamp", "metrics"}
    missing = required - set(msg)
    if missing:
        raise SchemaError(f"missing fields: {sorted(missing)}")

    domain = msg["domain"]
    if domain not in DOMAINS:
        raise SchemaError(f"unknown domain: {domain!r}")

    try:
        datetime.fromisoformat(str(msg["timestamp"]))
    except ValueError as exc:
        raise SchemaError(f"bad timestamp: {msg['timestamp']!r}") from exc

    metrics = msg["metrics"]
    if not isinstance(metrics, dict) or not metrics:
        raise SchemaError("metrics must be a non-empty dict")

    ranges = METRIC_RANGES[domain]
    for name, value in metrics.items():
        if name not in ranges:
            raise SchemaError(f"unknown metric {name!r} for domain {domain}")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SchemaError(f"metric {name} is not numeric: {value!r}")
        lo, hi = ranges[name]
        if not (lo <= float(value) <= hi):
            raise SchemaError(
                f"metric {name}={value} outside sane range [{lo}, {hi}]"
            )

    return TelemetryMessage(
        device_id=str(msg["device_id"]),
        domain=domain,
        zone=str(msg["zone"]),
        timestamp=str(msg["timestamp"]),
        metrics={k: float(v) for k, v in metrics.items()},
    )
