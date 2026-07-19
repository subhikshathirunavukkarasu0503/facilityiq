"""Render command outputs as terminal-style PNG images for the evidence pack.

Runs each evidence command, captures stdout, draws it onto a dark terminal
card with a title bar. Output: docs/screenshots/evNN_*.png
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"

AZ = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
GH = r"C:\Program Files\GitHub CLI\gh.exe"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
PYTEST = str(ROOT / ".venv" / "Scripts" / "pytest.exe")


def run(cmd: list[str], cwd: Path = ROOT) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd,
                       timeout=1200)
    return (r.stdout + r.stderr).strip()


def render(title: str, text: str, name: str, width: int = 1400) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        font = ImageFont.truetype("consola.ttf", 17)
        tfont = ImageFont.truetype("consolab.ttf", 18)
    except OSError:
        font = tfont = ImageFont.load_default()
    lines = text.splitlines() or [""]
    lh = 24
    height = 70 + lh * len(lines) + 30
    img = Image.new("RGB", (width, height), "#0d1117")
    d = ImageDraw.Draw(img)
    # title bar
    d.rectangle([0, 0, width, 44], fill="#161b22")
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        d.ellipse([16 + i * 26, 15, 30 + i * 26, 29], fill=c)
    d.text((100, 12), title, font=tfont, fill="#e6edf3")
    y = 60
    for line in lines:
        color = "#e6edf3"
        if "passed" in line or "OK" in line or "success" in line:
            color = "#3fb950"
        elif "FAIL" in line or "error" in line.lower():
            color = "#f85149"
        d.text((24, y), line[:160], font=font, fill=color)
        y += lh
    img.save(OUT / f"{name}.png")
    print("rendered", name)


def main() -> None:
    # 1. pytest with coverage (measured figure for Section 6)
    cov = run([PYTEST, "--cov", "--cov-report=term", "-q"])
    tail = "\n".join(cov.splitlines()[-22:])
    render("pytest --cov  ·  FacilityIQ full test suite", tail, "ev_coverage")

    # 2. CI run (GitHub Actions)
    ci = run([GH, "run", "list", "--limit", "4"])
    ci2 = run([GH, "run", "view", "--log-failed"]) or ""
    render("GitHub Actions  ·  gh run list  (repo: subhikshathirunavukkarasu0503/facilityiq)",
           ci, "ev_ci_runs")

    # 3. Azure blob lake
    blobs = run([AZ, "storage", "blob", "list", "--account-name", "fiqlake28091",
                 "--container-name", "telemetry", "--auth-mode", "login",
                 "--num-results", "300", "--query",
                 "[].{name:name}", "--output", "table"])
    lines = blobs.splitlines()
    summary = "\n".join(lines[:26] + [f"... ({len(lines) - 2} blobs total in container 'telemetry')"])
    acct = run([AZ, "storage", "account", "show", "--name", "fiqlake28091",
                "--resource-group", "rg-pSiddhi3.0-2026-01-sem4-Subhiksha",
                "--query", "{name:name, rg:resourceGroup, location:primaryLocation, sku:sku.name}",
                "--output", "table"])
    render("Azure CLI  ·  telemetry data lake on Blob Storage (account fiqlake28091)",
           acct + "\n\n" + summary, "ev_azure_lake")

    # 4. model metrics summary
    metrics = run([PY, "-c",
                   "import json;print(open('models/summary.json').read())"])
    ingest = run([PY, "-c", (
        "from pathlib import Path;"
        "files=list(Path('data/lake').rglob('*.jsonl'));"
        "n=sum(1 for f in files for _ in f.open());"
        "print(f'lake files: {len(files)}');print(f'telemetry records: {n}')")])
    render("ML model accuracy (held-out test sets)  +  lake ingestion stats",
           metrics + "\n" + ingest, "ev_model_metrics")

    # 5. git log
    log = run(["git", "log", "--oneline", "-10"])
    render("git log  ·  https://github.com/subhikshathirunavukkarasu0503/facilityiq",
           log, "ev_git_log")

    print("ALL RENDERED")


if __name__ == "__main__":
    main()
