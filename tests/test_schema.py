"""Unit tests: unified telemetry schema validation."""

import pytest

from facilityiq.ingestion.schema import SchemaError, validate_message


def good_msg(**overrides):
    msg = {
        "device_id": "hvac-ahu-01",
        "domain": "hvac",
        "zone": "floor1",
        "timestamp": "2026-07-01T10:00:00+00:00",
        "metrics": {"supply_temp_c": 16.0, "compressor_efficiency": 0.95},
    }
    msg.update(overrides)
    return msg


def test_valid_message_passes():
    validated = validate_message(good_msg())
    assert validated.device_id == "hvac-ahu-01"
    assert validated.metrics["supply_temp_c"] == 16.0


def test_missing_field_rejected():
    msg = good_msg()
    del msg["zone"]
    with pytest.raises(SchemaError, match="missing"):
        validate_message(msg)


def test_unknown_domain_rejected():
    with pytest.raises(SchemaError, match="domain"):
        validate_message(good_msg(domain="plumbing"))


def test_bad_timestamp_rejected():
    with pytest.raises(SchemaError, match="timestamp"):
        validate_message(good_msg(timestamp="yesterday"))


def test_empty_metrics_rejected():
    with pytest.raises(SchemaError, match="metrics"):
        validate_message(good_msg(metrics={}))


def test_unknown_metric_rejected():
    with pytest.raises(SchemaError, match="unknown metric"):
        validate_message(good_msg(metrics={"warp_drive": 1.0}))


def test_out_of_range_rejected():
    with pytest.raises(SchemaError, match="outside sane range"):
        validate_message(good_msg(metrics={"supply_temp_c": 500.0}))


def test_non_numeric_metric_rejected():
    with pytest.raises(SchemaError, match="not numeric"):
        validate_message(good_msg(metrics={"supply_temp_c": "hot"}))


def test_wrong_domain_metric_rejected():
    with pytest.raises(SchemaError, match="unknown metric"):
        validate_message(good_msg(domain="energy",
                                  metrics={"supply_temp_c": 16.0}))
