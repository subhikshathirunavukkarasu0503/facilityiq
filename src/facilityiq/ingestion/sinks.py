"""Telemetry sinks: local JSONL data lake and Azure IoT Hub.

The local sink mirrors the Blob Storage landing-zone layout
(domain/date/device.jsonl) so the ML pipeline reads identically whether data
arrived via Azure or was generated locally.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .schema import TelemetryMessage, validate_message

DEFAULT_LAKE = Path(__file__).resolve().parents[3] / "data" / "lake"


class LocalLakeSink:
    """Append validated telemetry to a partitioned JSONL data lake."""

    def __init__(self, root: Path | str = DEFAULT_LAKE):
        self.root = Path(root)
        self.written = 0
        self.rejected = 0

    def write(self, msg: dict) -> TelemetryMessage | None:
        try:
            validated = validate_message(msg)
        except Exception:
            self.rejected += 1
            return None
        date = validated.timestamp[:10]
        path = self.root / validated.domain / date / f"{validated.device_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(validated.to_dict()) + "\n")
        self.written += 1
        return validated


class IoTHubSink:
    """Send validated telemetry to Azure IoT Hub (device-to-cloud).

    Requires IOTHUB_DEVICE_CONNECTION_STRING in the environment. Import of the
    Azure SDK is deferred so local development never needs it installed.
    """

    def __init__(self, connection_string: str | None = None):
        conn = connection_string or os.environ.get("IOTHUB_DEVICE_CONNECTION_STRING")
        if not conn:
            raise RuntimeError("IOTHUB_DEVICE_CONNECTION_STRING not set")
        from azure.iot.device import IoTHubDeviceClient  # deferred import

        self.client = IoTHubDeviceClient.create_from_connection_string(conn)
        self.client.connect()
        self.written = 0
        self.rejected = 0

    def write(self, msg: dict) -> TelemetryMessage | None:
        try:
            validated = validate_message(msg)
        except Exception:
            self.rejected += 1
            return None
        from azure.iot.device import Message

        payload = Message(json.dumps(validated.to_dict()))
        payload.content_type = "application/json"
        payload.content_encoding = "utf-8"
        payload.custom_properties["domain"] = validated.domain
        self.client.send_message(payload)
        self.written += 1
        return validated

    def close(self) -> None:
        self.client.shutdown()
