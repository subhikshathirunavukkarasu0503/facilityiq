"""Run the fleet simulation and land telemetry in the data lake.

Usage:
    python -m facilityiq.simulators.run_simulation [--days 14] [--sink local|iothub]
"""

from __future__ import annotations

import argparse
import time

from ..ingestion.sinks import LocalLakeSink, IoTHubSink
from .devices import simulate_fleet


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=float, default=14.0)
    parser.add_argument("--sink", choices=["local", "iothub"], default="local")
    parser.add_argument("--limit", type=int, default=0,
                        help="stop after N messages (0 = all)")
    args = parser.parse_args()

    sink = IoTHubSink() if args.sink == "iothub" else LocalLakeSink()
    t0 = time.time()
    for i, msg in enumerate(simulate_fleet(days=args.days)):
        sink.write(msg)
        if args.limit and i + 1 >= args.limit:
            break
    elapsed = time.time() - t0
    print(f"written={sink.written} rejected={sink.rejected} in {elapsed:.1f}s")
    if hasattr(sink, "close"):
        sink.close()


if __name__ == "__main__":
    main()
