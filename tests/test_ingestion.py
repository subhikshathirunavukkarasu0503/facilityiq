"""Integration tests: simulator -> validation -> local lake sink."""

import json

from facilityiq.ingestion.sinks import LocalLakeSink
from facilityiq.simulators.devices import simulate_fleet


def test_sink_writes_partitioned_jsonl(tmp_path):
    sink = LocalLakeSink(tmp_path)
    for i, msg in enumerate(simulate_fleet(days=1.0)):
        sink.write(msg)
        if i >= 199:
            break
    assert sink.written == 200
    assert sink.rejected == 0
    files = list(tmp_path.rglob("*.jsonl"))
    assert files, "lake files must exist"
    # partition layout: domain/date/device.jsonl
    rel = files[0].relative_to(tmp_path)
    assert len(rel.parts) == 3
    line = json.loads(files[0].read_text().splitlines()[0])
    assert {"device_id", "domain", "zone", "timestamp", "metrics"} <= set(line)


def test_sink_rejects_invalid_and_keeps_going(tmp_path):
    sink = LocalLakeSink(tmp_path)
    assert sink.write({"garbage": True}) is None
    good = next(iter(simulate_fleet(days=0.1)))
    assert sink.write(good) is not None
    assert sink.rejected == 1
    assert sink.written == 1


def test_all_three_domains_land_in_lake(tmp_path):
    sink = LocalLakeSink(tmp_path)
    for msg in simulate_fleet(days=0.5):
        sink.write(msg)
    domains = {p.name for p in tmp_path.iterdir()}
    assert domains == {"hvac", "energy", "occupancy"}
