"""Great Expectations validation for the raw FacilityIQ telemetry lake.

The validator reads every JSONL record, flattens metric names into columns,
and runs a domain-specific expectation suite. It is intentionally independent
of Azure so the same checks protect local, Blob, and IoT Hub landing paths.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from facilityiq.ingestion.schema import DOMAINS, METRIC_RANGES

REQUIRED = ("device_id", "domain", "zone", "timestamp")


@dataclass
class DomainQualityResult:
    domain: str
    records: int
    expectations: int
    successful: int
    failed: int
    success: bool


@dataclass
class LakeQualityReport:
    files: int
    records: int
    duplicates: int
    domains: dict[str, DomainQualityResult]

    @property
    def success(self) -> bool:
        return self.duplicates == 0 and all(x.success for x in self.domains.values())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["success"] = self.success
        return payload


def load_lake(lake: Path) -> tuple[pd.DataFrame, int]:
    files = sorted(lake.rglob("*.jsonl"))
    rows: list[dict[str, Any]] = []
    for path in files:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON: {path}:{line_no}: {exc}") from exc
            row = {name: raw.get(name) for name in REQUIRED}
            metrics = raw.get("metrics") or {}
            if isinstance(metrics, dict):
                row.update(metrics)
            rows.append(row)
    if not rows:
        raise ValueError(f"no telemetry records found under {lake}")
    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    return frame, len(files)


def _domain_suite(domain: str, columns: set[str]) -> gx.ExpectationSuite:
    ex = gx.expectations
    suite = gx.ExpectationSuite(name=f"facilityiq_{domain}_quality")
    for column in REQUIRED:
        suite.add_expectation(ex.ExpectColumnValuesToNotBeNull(column=column))
    suite.add_expectation(ex.ExpectColumnValuesToBeInSet(column="domain", value_set=[domain]))
    for metric, (minimum, maximum) in METRIC_RANGES[domain].items():
        if metric in columns:
            suite.add_expectation(ex.ExpectColumnValuesToNotBeNull(column=metric))
            suite.add_expectation(ex.ExpectColumnValuesToBeBetween(
                column=metric, min_value=minimum, max_value=maximum))
    return suite


def validate_lake(lake: str | Path) -> LakeQualityReport:
    frame, file_count = load_lake(Path(lake))
    duplicates = int(frame.duplicated(subset=["device_id", "timestamp"]).sum())
    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas("facilityiq_telemetry")
    results: dict[str, DomainQualityResult] = {}

    for domain in DOMAINS:
        subset = frame.loc[frame["domain"] == domain].copy()
        if subset.empty:
            results[domain] = DomainQualityResult(domain, 0, 1, 0, 1, False)
            continue
        asset = source.add_dataframe_asset(name=f"{domain}_telemetry")
        definition = asset.add_batch_definition_whole_dataframe("whole_lake")
        suite = _domain_suite(domain, set(subset.columns))
        context.suites.add(suite)
        validation = gx.ValidationDefinition(
            name=f"validate_{domain}", data=definition, suite=suite)
        context.validation_definitions.add(validation)
        outcome = validation.run(
            batch_parameters={"dataframe": subset}, result_format="SUMMARY")
        stats = outcome.statistics
        results[domain] = DomainQualityResult(
            domain=domain,
            records=len(subset),
            expectations=int(stats["evaluated_expectations"]),
            successful=int(stats["successful_expectations"]),
            failed=int(stats["unsuccessful_expectations"]),
            success=bool(outcome.success),
        )

    return LakeQualityReport(file_count, len(frame), duplicates, results)
