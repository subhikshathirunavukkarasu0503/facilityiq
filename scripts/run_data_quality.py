"""Run FacilityIQ's Great Expectations data-quality suite."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from facilityiq.qa.data_quality import validate_lake

p = argparse.ArgumentParser()
p.add_argument("--lake", type=Path, default=Path("data/lake"))
p.add_argument("--output", type=Path, default=Path("docs/evidence/final/data_quality_report.json"))
a = p.parse_args()
report = validate_lake(a.lake)
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
print(json.dumps(report.to_dict(), indent=2))
raise SystemExit(0 if report.success else 1)
