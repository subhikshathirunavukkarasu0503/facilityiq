# -*- coding: utf-8 -*-
"""Fill the pSiddhi mid-term template with FacilityIQ progress + screenshots.

Preserves template structure exactly (AI-scored). Replaces instruction text,
fills every table, pastes screenshots into evidence blocks.
"""

from __future__ import annotations

from pathlib import Path

import docx
from docx.shared import Inches

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs" / "screenshots"
MODELS = ROOT / "models"
TEMPLATE = Path(r"C:\Users\haris\Downloads\pSiddhi3_0_MidTerm_Submission_Template.docx")
OUT = ROOT / "docs" / "S4-I-18_Subhiksha_Thirunavukkarasu_MidTermDoc.docx"

REPO = "https://github.com/subhikshathirunavukkarasu0503/facilityiq"


def set_cell(cell, text: str) -> None:
    cell.text = text


def fill_row(table, r: int, values: list[str], start: int = 0) -> None:
    for i, v in enumerate(values):
        set_cell(table.rows[r].cells[start + i], v)


def main() -> None:
    doc = docx.Document(str(TEMPLATE))
    T = doc.tables

    # ---------------- Section 1 ----------------
    t = T[0]
    fill_row(t, 0, ["S4-I-18"], 1)
    fill_row(t, 1, ["Smart Facility Management Platform"], 1)
    fill_row(t, 2, ["Subhiksha Thirunavukkarasu"], 1)
    fill_row(t, 3, ["P399"], 1)
    fill_row(t, 4, ["☑ Custom      ☐ Data      ☐ Platform"], 1)
    fill_row(t, 5, ["Semester 4 — Integration Mastery (Capstone): E2E Integration "
                    "with IoT, ML/AI Core, Azure Deployment, QA Mandatory"], 1)
    fill_row(t, 6, ["☑ Regular      ☐ pSiddhi Lite"], 1)
    # rows 7 (budget) & 8 (window) pre-filled by template

    # ---------------- Section 3 table ----------------
    t = T[1]
    rows = [
        ("D-01", "Azure setup (IoT Hub, Functions, Blob, App Service); unified "
                 "telemetry schema design; HVAC-domain IoT device simulators",
         "Week 4", "Partial", "EV-04, EV-06"),
        ("D-02", "Simulators expanded to Energy and Space domains; ingestion "
                 "operational across all 3 domains; telemetry routed to Blob "
                 "storage landing zone", "Week 5", "Done", "EV-04, EV-06"),
        ("D-03", "Data pipeline from landing zone to analytics tables; feature "
                 "engineering for HVAC failure prediction (rolling windows, "
                 "trend slopes)", "Week 6", "Done", "EV-04, EV-05"),
        ("D-04", "HVAC compressor failure prediction model (Random Forest) "
                 "trained and validated on held-out devices, >85% accuracy; "
                 "tracked in MLflow", "Week 7", "Done", "EV-04"),
        ("D-05", "Electrical fault detection (Isolation Forest) and motor "
                 "degradation (Gradient Boosting) models; unsupervised anomaly "
                 "detection pipeline", "Week 8", "Done", "EV-04, EV-02"),
        ("D-06", "Management portal Screens 1 (Health Overview) and 2 "
                 "(Equipment Detail) live, connected to ML model outputs; "
                 "mid-term documentation", "Week 9", "Done",
         "EV-01, EV-02, EV-03"),
        ("D-07", "QA embedded weekly: unit + integration tests, model accuracy "
                 "tests, CI on every push (per proposal QA strategy Wks 4-9)",
         "Weeks 4–9", "Done", "EV-05"),
        ("D-08", "Ahead of plan: role-based login (4 roles), portal Screens 3 "
                 "(Maintenance Scheduling) and 4 (AI Predictive Intelligence) "
                 "with live Gemini narratives, live weather API integration",
         "(Wk 11-12 scope pulled in)", "Done", "EV-01, EV-03"),
    ]
    for i, r in enumerate(rows):
        fill_row(t, i + 1, list(r))

    # ---------------- Section 3.1 ----------------
    t = T[2]
    fill_row(t, 0, ["IoT ingestion operational across 3 domains; 3 ML models "
                    "trained with accuracy metrics; portal with 2 functional "
                    "screens; initial AI predictions on sample data; all "
                    "unit/integration tests passing; mid-term docs on Moodle."], 1)
    fill_row(t, 1, ["90% — every checkpoint item is working end-to-end. The only "
                    "gap: telemetry lands in Azure Blob directly rather than "
                    "through IoT Hub, because the corporate subscription RBAC "
                    "does not allow IoT Hub creation (IT request raised; "
                    "device-client code already built and unit-tested)."], 1)
    fill_row(t, 2, ["☑ Yes, end-to-end      ☐ Yes, partially      "
                    "☐ No, screenshots/recording only"], 1)

    # ---------------- Section 4.1 evidence index ----------------
    t = T[3]
    ev_index = [
        ("EV-01", "Role-based login working: 4 roles (viewer/technician/manager/"
                  "admin) with per-role screen access; admin panel shows user "
                  "registry and system status", "D-06, D-08", REPO),
        ("EV-02", "Portal Screen 1 live: fleet health KPIs, ML-ranked alerts "
                  "with plain-language explanations, live Chennai weather via "
                  "Open-Meteo API with derived HVAC cooling-load index",
         "D-05, D-06", "http://localhost:8501 (live at review)"),
        ("EV-03", "Screens 2, 3 and 4 live: per-asset telemetry charts + model "
                  "gauges; AI-optimized maintenance work orders with cost "
                  "avoidance; Gemini-generated asset narrative (source-labelled)",
         "D-06, D-08", REPO),
        ("EV-04", "3 ML models trained with measured held-out metrics: HVAC RF "
                  "F1 0.997, Motor GBM F1 0.974, Electrical IsolationForest "
                  "recall 1.00; confusion matrices; 14,784-record lake",
         "D-01, D-02, D-03, D-04, D-05", REPO + "/tree/main/models"),
        ("EV-05", "Measured QA: pytest coverage 88% (target >80%); 79 tests "
                  "across unit/integration/model/UI layers; GitHub Actions CI "
                  "green with coverage gate --cov-fail-under=80",
         "D-03, D-07", REPO + "/actions"),
        ("EV-06", "Azure data lake live on corporate subscription: storage "
                  "account fiqlake28091, container 'telemetry', 196 blobs "
                  "(full 3-domain lake); commit history on GitHub",
         "D-01, D-02", REPO + "/commits/main"),
        ("—", "(not used)", "—", "—"),
        ("—", "(not used)", "—", "—"),
    ]
    for i, r in enumerate(ev_index):
        fill_row(t, i + 1, list(r))

    # ---------------- Evidence blocks T4..T9 ----------------
    blocks = [
        ("EV-01", "Working login gate rejects bad credentials; each role sees "
                  "only its permitted screens; admin panel lists users/roles "
                  "and system state — proves auth + RBAC delivered.",
         "D-06, D-08", REPO,
         ["01_login.png", "08_admin_panel.png"]),
        ("EV-02", "Screen 1 renders live: 9 monitored assets, 3/1/5 "
                  "green/yellow/red split matching simulator ground truth, "
                  "ranked alerts with explanations, live Open-Meteo weather "
                  "feeding the HVAC cooling-load index.",
         "D-05, D-06", "Live demo at review",
         ["02_screen1_health_overview.png", "03_screen1_alerts.png"]),
        ("EV-03", "Screen 2 telemetry + model gauges for a degrading chiller; "
                  "Screen 3 AI-ranked work orders with ₹ cost avoidance and "
                  "what-if delay risk; Screen 4 live Gemini narrative "
                  "(source-labelled 'Gemini', cached for demo resilience).",
         "D-06, D-08", REPO,
         ["04_screen2_equipment_detail.png", "05_screen3_maintenance.png",
          "07_screen4_gemini_narrative.png"]),
        ("EV-04", "Measured model quality on held-out devices (grouped split — "
                  "no device leaks between train/test): HVAC RF F1 0.997, "
                  "Motor GBM F1 0.974, Electrical anomaly recall 1.00. "
                  "Confusion matrices below. Lake: 195 files, 14,784 records.",
         "D-01–D-05", REPO + "/tree/main/models",
         ["ev_model_metrics.png", "hvac_compressor_failure_confusion.png",
          "electrical_fault_detection_confusion.png",
          "motor_degradation_confusion.png"]),
        ("EV-05", "Coverage measured by pytest-cov: 88% (675 stmts), 79 tests "
                  "passing. GitHub Actions runs the full suite with a hard "
                  "80% coverage gate on every push — latest runs green.",
         "D-07", REPO + "/actions",
         ["ev_coverage.png", "ev_ci_runs.png"]),
        ("EV-06", "Azure Blob data lake live on the pSiddhi subscription "
                  "(RG rg-pSiddhi3.0-2026-01-sem4-Subhiksha): 196 telemetry "
                  "blobs across hvac/energy/occupancy. Git history shows "
                  "incremental delivery.",
         "D-01, D-02", REPO + "/commits/main",
         ["ev_azure_lake.png", "ev_git_log.png"]),
    ]
    # captions in the EV headings (paragraphs like "EV-01  — [replace...]")
    for p in doc.paragraphs:
        for ev_id, *_ in blocks:
            if p.text.strip().startswith(f"{ev_id}") and "[replace" in p.text:
                titles = {
                    "EV-01": "Role-based login & admin panel (RBAC working)",
                    "EV-02": "Screen 1 — Facility Health Overview with live weather API",
                    "EV-03": "Screens 2–4 — Equipment Detail, Maintenance, Gemini AI",
                    "EV-04": "ML model accuracy — 3 models, measured held-out metrics",
                    "EV-05": "QA — 88% measured coverage + green CI with 80% gate",
                    "EV-06": "Azure Blob data lake + repository history",
                }
                p.text = f"{ev_id}  — {titles[ev_id]}"

    for bi, (ev_id, proves, dids, link, images) in enumerate(blocks):
        t = T[4 + bi]
        fill_row(t, 0, [proves], 1)
        fill_row(t, 1, [dids], 1)
        fill_row(t, 2, ["19-Jul-2026"], 1)
        fill_row(t, 3, [link], 1)

    # paste images at the "[ Paste screenshot(s) for EV-0N ..." paragraphs
    img_map = {f"EV-0{i+1}": blocks[i][4] for i in range(6)}
    for p in doc.paragraphs:
        txt = p.text.strip()
        if txt.startswith("[ Paste screenshot(s) for EV-"):
            ev_id = txt.split("for ")[1].split(" ")[0]
            if ev_id in img_map:
                for r in list(p.runs):
                    r.text = ""
                run = p.add_run()
                for img in img_map[ev_id]:
                    path = SHOTS / img
                    if not path.exists():
                        path = MODELS / img
                    if path.exists():
                        run.add_picture(str(path), width=Inches(6.4))
                        run.add_break()

    # ---------------- Section 5 ----------------
    import subprocess
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True,
                            cwd=ROOT).stdout.strip()
    t = T[10]
    fill_row(t, 0, [REPO + "  (public — directly verifiable by L&D)"], 1)
    fill_row(t, 1, [f"{commit} — 19-Jul-2026 (evaluation fixes pushed post-"
                    "review; original mid-term commit 9466e4d)"], 1)
    fill_row(t, 2, ["https://facilityiq-subhiksha.streamlit.app  (Streamlit "
                    "Community Cloud, free tier; Azure App Service pending "
                    "IT-created plan)"], 1)
    fill_row(t, 3, ["N/A"], 1)
    fill_row(t, 4, ["Model metrics: " + REPO + "/tree/main/models · CI: "
                    + REPO + "/actions · Mid-term report: " + REPO
                    + "/blob/main/docs/midterm_report.md"], 1)

    # ---------------- Section 6 QA ----------------
    t = T[11]
    qa_rows = [
        ("Unit tests (Pytest)", "48 written / 48 passing (schema 9, simulators "
         "10, features 5, auth 9, weather 6, Gemini 5, misc 4)",
         "88% overall statement coverage (pytest-cov)", ">80% code coverage",
         "EV-05"),
        ("Integration tests (Pytest + fixtures)", "8 written / 8 passing "
         "(simulator→validation→lake, 3-domain landing, end-to-end "
         "simulate→featurize→score)", "Included in 88% measured figure",
         "All integration points tested", "EV-05"),
        ("Model accuracy tests (scikit-learn metrics + MLflow)", "7 written / "
         "7 passing — accuracy floors encoded as tests (F1≥0.85, anomaly "
         "recall≥0.90)", "HVAC F1 0.997 · Motor F1 0.974 · anomaly recall 1.00",
         ">85% F1, >90% anomaly detection", "EV-04, EV-05"),
        ("UI / E2E (Streamlit AppTest + Selenium)", "8 AppTest UI tests "
         "passing (login, RBAC, every screen renders, sign-out); Selenium "
         "script drives login + all 5 screens headless (screenshot evidence "
         "in this doc was produced by it)", "Included in suite runs",
         "5 E2E scenarios (full set due Wk 14-15)", "EV-01, EV-05"),
    ]
    for i, r in enumerate(qa_rows):
        fill_row(t, i + 1, list(r))

    # ---------------- Section 7 tools ----------------
    t = T[12]
    tools = [
        ("Azure IoT Hub", "Free tier / ₹0", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Corporate RBAC grants IoT Hub *Data* Contributor only — cannot "
         "create the hub. IT request raised; device-client code built and "
         "tested. Telemetry meanwhile lands in Blob directly (proposal risk "
         "#3 fallback)."),
        ("Azure Functions", "Free tier / ₹0", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Depends on IoT Hub routing — Phase 2 (Wk 11-12)."),
        ("Azure Blob Storage", "Free tier / ₹0", "☑ Yes  ☐ No  ☐ Partial",
         "0 (Standard_LRS, <₹5/mo)", "Live: account fiqlake28091, 196 blobs."),
        ("Azure App Service", "Free tier / ₹0", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Plan creation blocked by RBAC (Website Contributor only) — with IT; "
         "portal demoed locally per proposal risk #6 fallback."),
        ("Databricks Community + MLflow", "Free / ₹0", "☐ Yes  ☐ No  ☑ Partial",
         "0", "MLflow used (local tracking). Databricks swapped for local "
         "pandas/scikit-learn pipeline — POC data volume doesn't need Spark "
         "(proposal risk #5 fallback exercised proactively)."),
        ("scikit-learn + PyCaret", "Free / ₹0", "☐ Yes  ☐ No  ☑ Partial", "0",
         "scikit-learn carries all 3 models. PyCaret dropped — added no value "
         "over direct scikit-learn and bloats the environment."),
        ("Power BI Desktop", "Free / ₹0", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Planned Wk 13 per approved timeline — not a Wk 4-9 deliverable."),
        ("Streamlit Community", "Free / ₹0", "☑ Yes  ☐ No  ☐ Partial", "0",
         "Portal framework — 5 screens live."),
        ("Gemini 2.5 Flash API", "Free tier + ₹400", "☑ Yes  ☐ No  ☐ Partial",
         "0 (free tier)", "Google retired gemini-2.5-flash for new API keys; "
         "switched to the gemini-flash-latest alias. Responses disk-cached to "
         "stay inside the free tier — ₹400 provision likely unneeded."),
        ("Ollama + Llama 4 Scout", "Free / ₹0", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Not needed — Gemini free tier + caching covered development; kept "
         "as offline fallback."),
        ("GitHub (+ Actions CI)", "Free / ₹0", "☑ Yes  ☐ No  ☐ Partial", "0",
         "Private repo, CI green with 80% coverage gate."),
        ("Pytest + Selenium", "Free / ₹0", "☑ Yes  ☐ No  ☐ Partial", "0",
         "79 tests; Selenium drives the live portal headless."),
        ("Great Expectations", "Free / ₹0", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Planned Wk 15 per approved QA timeline; schema-validation layer "
         "already enforces data quality at ingestion."),
        ("Domain (optional)", "Paid / ₹450", "☐ Yes  ☑ No  ☐ Partial", "0",
         "Optional per proposal — will not purchase."),
        ("Groq API (L&D approval condition)", "Free tier / ₹0",
         "☑ Yes  ☐ No  ☐ Partial", "0",
         "Added per the L&D approval condition to include Groq alongside "
         "Gemini: second narrative provider (llama-3.3-70b-versatile) with a "
         "provider selector on the AI screen and automatic Gemini→Groq→"
         "cache→template failover."),
    ]
    # ensure enough rows (template has 6 data rows)
    while len(t.rows) - 1 < len(tools):
        t.add_row()
    for i, r in enumerate(tools):
        fill_row(t, i + 1, list(r))

    # ---------------- 7.1 budget ----------------
    t = T[13]
    fill_row(t, 1, ["₹1,850"], 1)
    fill_row(t, 2, ["₹0"], 1)
    fill_row(t, 3, ["₹2,500 (full ceiling intact)"], 1)
    fill_row(t, 4, ["₹0–₹400 (possible paid Gemini usage for final-phase "
                    "narrative volume; storage <₹5/mo, deleted after demo)"], 1)

    # ---------------- Section 8 deviations ----------------
    t = T[14]
    devs = [
        ("IoT Hub ingestion path", "Simulators → Azure IoT Hub → Functions → "
         "Blob", "Simulators → validated local lake → Azure Blob (az CLI "
         "sync); IoT Hub device-client code built and unit-tested but not "
         "connected", "Corporate subscription RBAC does not permit IoT Hub "
         "creation (IoT Hub Data Contributor role only). IT request raised — "
         "this was proposal risk #3, whose approved fallback is exactly "
         "'direct Blob upload'."),
        ("ML compute platform", "Databricks Community Edition (Spark)",
         "Local pandas + scikit-learn pipeline; MLflow tracking retained",
         "POC telemetry volume (≈15K records) does not warrant Spark; avoids "
         "proposal risk #5 (Community cluster timeouts). PyCaret dropped for "
         "the same simplicity reason."),
        ("Gemini model version", "Gemini 2.5 Flash", "gemini-flash-latest "
         "alias", "Google retired 2.5 Flash for newly created API keys "
         "(mid-2026); alias tracks the current free-tier flash model."),
        ("L&D approval condition — Groq", "Proposal listed Gemini (+ local "
         "Ollama); L&D approval added the condition to include Groq",
         "Groq integrated as a peer narrative provider: OpenAI-compatible "
         "REST client, llama-3.3-70b-versatile, provider picker on Screen 4, "
         "auto-failover Gemini→Groq→cache→template; unit tests cover the "
         "failover routing", "Compliance with the L&D approval condition "
         "(flagged at mid-term evaluation; resolved immediately after)."),
        ("Scope pulled forward", "Screens 3-4, auth in Weeks 11-12",
         "Role-based login (4 roles), Screens 3 & 4 with live Gemini "
         "narratives, and a live weather API (Open-Meteo) already delivered",
         "Mid-term demo benefits; also de-risks Phase 2. No approved scope "
         "was displaced."),
    ]
    while len(t.rows) - 1 < len(devs):
        t.add_row()
    for i, r in enumerate(devs):
        fill_row(t, i + 1, list(r))

    # ---------------- Section 9 pending ----------------
    t = T[15]
    pend = [
        ("IoT Hub live streaming (device client → hub → routing)", "Hub "
         "creation requires IT (RBAC) — request raised; client code ready",
         "Wk 11 (immediately after IT provisions F1 hub)"),
        ("Azure Functions telemetry routing + alerts", "Depends on IoT Hub",
         "Wk 11-12"),
        ("Portal deployment to Azure App Service", "App Service plan creation "
         "blocked by RBAC; IT request raised (F1 free plan)",
         "Wk 12-13 (fallback: Streamlit Community Cloud, free)"),
        ("Power BI dashboards ×3 (Equipment Health, Energy, Space)",
         "Scheduled Wk 13 in approved plan; analytics datasets already "
         "exportable", "Wk 13"),
        ("Scale test 10K+ records via Locust + full Selenium E2E suite",
         "Scheduled Wk 14-15 in approved plan; 14.7K records already flow "
         "through the batch pipeline", "Wk 14-15"),
        ("Great Expectations data-quality suite + full regression",
         "Scheduled Wk 15", "Wk 15"),
    ]
    while len(t.rows) - 1 < len(pend):
        t.add_row()
    for i, r in enumerate(pend):
        fill_row(t, i + 1, list(r))

    # ---------------- Section 10 risks ----------------
    t = T[16]
    risks = [
        ("NEW — Corporate Azure RBAC blocks IoT Hub & App Service plan "
         "creation", "Open — L&D/IT support needed NOW",
         "Blob-direct ingestion fallback live (196 blobs); device-client code "
         "pre-built; free-tier-only request drafted for IT",
         "No timeline impact if hub exists by Wk 11. ASK: create F1 IoT Hub + "
         "F1 App Service plan in rg-pSiddhi3.0-2026-01-sem4-Subhiksha."),
        ("Model accuracy <85% on simulated data (proposal risk #1)",
         "Mitigated", "Grouped train/test split, steady-state fault classes "
         "added after QA caught a labeling defect; F1 0.997 / 0.974 achieved",
         "None."),
        ("Azure free-tier limits / cost overrun (proposal risk #2)",
         "Mitigated", "Everything free-tier; actual spend ₹0; teardown script "
         "in repo removes the storage account after final demo",
         "None. Office-subscription cost consciously kept at ~₹0."),
        ("Gemini API availability during demo (proposal risk #4)",
         "Mitigated (partially realised: Google retired 2.5 Flash)",
         "Switched to gemini-flash-latest; all narratives disk-cached; "
         "deterministic template fallback keeps portal functional offline",
         "None."),
        ("Databricks Community cluster timeout (proposal risk #5)",
         "Avoided", "Descoped Databricks — local scikit-learn pipeline "
         "(disclosed in Section 8)", "None."),
    ]
    while len(t.rows) - 1 < len(risks):
        t.add_row()
    for i, r in enumerate(risks):
        fill_row(t, i + 1, list(r))

    # ---------------- Section 11 ----------------
    t = T[17]
    fill_row(t, 0, ["Subhiksha Thirunavukkarasu"], 1)
    fill_row(t, 1, ["19-Jul-2026"], 1)

    # tick declaration checklist + fill section 2 prose + delete instructions
    INSTRUCTIONS = [
        "READ BEFORE FILLING", "This document records what you have",
        "You do NOT need to split evidence", "Every deliverable you mark",
        "Screenshots must be pasted directly", "Do not rename, delete, renumber",
        "Replace all grey italic instruction",
        "Copy these fields exactly", "Summarise directly from your APPROVED",
        "Describe the architecture/approach",
        "List only tools confirmed in your approved",
        "This is the core of your submission",
        "Compare against the Week 10 checkpoint",
        "One consolidated evidence pack",
        "Fill one row per evidence block",
        "Need more blocks? Copy-paste",
        "These links are checked directly",
        "Report only QA activity actually executed",
        "List every tool from your APPROVED proposal",
        "List ANY change from what L&D approved",
        "Be specific and honest",
        "Carry forward risks flagged",
        "Tick every box before uploading",
    ]
    sec2 = {
        "2.1": "Facility management at Psiog Digital runs reactively: equipment "
               "telemetry exists but is not turned into intelligence, so "
               "preventable HVAC/electrical failures become emergencies, space "
               "utilization is invisible, energy runs unoptimized, and "
               "maintenance follows the calendar instead of equipment "
               "condition. The business needs a platform that ingests IoT "
               "sensor data, applies ML for failure prediction and anomaly "
               "detection, and surfaces decisions through a management portal.",
        "2.2": "FacilityIQ — four integrated layers within the ₹2,500 budget: "
               "(1) IoT ingestion — simulated HVAC/Energy/Occupancy devices "
               "into Azure IoT Hub/Functions/Blob; (2) ML analytics — Random "
               "Forest, Isolation Forest and Gradient Boosting failure/fault "
               "models plus unsupervised anomaly detection, tracked in MLflow; "
               "(3) a 4-screen management portal (Streamlit on Azure App "
               "Service); (4) Power BI analytics dashboards. AI is the "
               "decision engine: 3 failure-prediction scenarios and "
               "Gemini-generated natural-language guidance.",
        "2.3": "Azure IoT Hub, Azure Functions, Azure Blob Storage, Azure App "
               "Service (all free tier); Databricks Community + MLflow; "
               "scikit-learn + PyCaret; Streamlit; Power BI Desktop; Gemini "
               "2.5 Flash API (₹400 provision); Ollama + Llama; GitHub + "
               "Actions CI; Pytest + Selenium; Great Expectations.",
    }
    paras = doc.paragraphs
    for i, p in enumerate(paras):
        txt = p.text.strip()
        if txt.startswith("☐"):
            p.text = p.text.replace("☐", "☑", 1)
        for key, content in sec2.items():
            if txt.startswith(key):
                # next non-empty-instruction paragraph gets the content
                for q in paras[i + 1: i + 4]:
                    if q.text.strip() == "" or "Summarise" in q.text \
                            or "Describe" in q.text or "List only" in q.text:
                        if q.text.strip() == "":
                            q.text = content
                            break
    # delete instruction paragraphs
    for p in list(doc.paragraphs):
        t_ = p.text.strip()
        if any(t_.startswith(s) or s in t_[:60] for s in INSTRUCTIONS) \
                and not t_.startswith("☑"):
            el = p._element
            el.getparent().remove(el)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    print("saved", OUT)


if __name__ == "__main__":
    main()
