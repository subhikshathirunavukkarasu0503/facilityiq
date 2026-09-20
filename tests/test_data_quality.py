import json
from pathlib import Path
import pytest
from facilityiq.qa.data_quality import load_lake, validate_lake

LAKE = Path(__file__).resolve().parents[1] / "data" / "lake"

@pytest.mark.skipif(not LAKE.exists(), reason="telemetry lake not present")
def test_committed_lake_passes_great_expectations():
    report = validate_lake(LAKE)
    assert report.success
    assert report.records >= 10_000
    assert set(report.domains) == {"hvac", "energy", "occupancy"}
    assert all(result.failed == 0 for result in report.domains.values())


def test_invalid_json_is_reported_with_file_and_line(tmp_path):
    bad = tmp_path / "hvac" / "2026-01-01"
    bad.mkdir(parents=True)
    (bad / "bad.jsonl").write_text('{"broken":', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_lake(tmp_path)


def test_missing_domain_fails_quality_gate(tmp_path):
    p = tmp_path / "hvac" / "2026-01-01"
    p.mkdir(parents=True)
    row = {"device_id":"x", "domain":"hvac", "zone":"z",
           "timestamp":"2026-01-01T00:00:00+00:00",
           "metrics":{"supply_temp_c":20,"return_temp_c":24,
                      "humidity_pct":50,"compressor_efficiency":0.9,
                      "vibration_mm_s":1,"filter_dp_pa":100,"motor_temp_c":40}}
    (p / "x.jsonl").write_text(json.dumps(row)+"\n", encoding="utf-8")
    report = validate_lake(tmp_path)
    assert not report.success
    assert report.domains["energy"].failed == 1
