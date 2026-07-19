# FacilityIQ — Project Handbook

Quick reference for every link, credential location, and command.
(Secrets are NOT stored in this file — see "Where secrets live".)

## Links

| What | URL |
|---|---|
| GitHub repo | https://github.com/subhikshathirunavukkarasu0503/facilityiq |
| CI (GitHub Actions) | https://github.com/subhikshathirunavukkarasu0503/facilityiq/actions |
| Model metrics | https://github.com/subhikshathirunavukkarasu0503/facilityiq/tree/main/models |
| Mid-term report | docs/midterm_report.md |
| Mid-term submission doc | docs/S4-I-18_Subhiksha_Thirunavukkarasu_MidTermDoc.docx |
| Portal (local) | http://localhost:8501 |
| Portal (cloud) | via https://share.streamlit.io (app under GitHub account) |
| Azure resources | portal.azure.com → RG `rg-pSiddhi3.0-2026-01-sem4-Subhiksha` → storage `fiqlake28091`, container `telemetry` |
| Gemini key management | https://aistudio.google.com/apikey |
| Weather API | https://open-meteo.com (keyless, free) |

## Portal demo accounts (POC credential store: `src/facilityiq/portal/auth.py`)

| Username | Password | Role |
|---|---|---|
| viewer | viewer@123 | Executive viewer — Health Overview only |
| tech | tech@123 | Technician — + Equipment Detail, AI screen |
| manager | manager@123 | Manager — + Maintenance Scheduling |
| admin | admin@123 | Admin — all screens + Admin panel |

## Service accounts

| Service | Account |
|---|---|
| GitHub | subhikshathirunavukkarasu0503 (gh CLI authenticated on dev machine) |
| Azure | subhiksha.thirunavukkarasu@psiog.com (az CLI authenticated; OFFICE subscription — free tiers only!) |
| Google AI Studio | subhikshathirunavukkarasu0503@gmail.com |

## Where secrets live

- **Gemini API key**: local `.env` (gitignored) and Streamlit Cloud → app → Settings → Secrets (`GEMINI_API_KEY = "..."`). Rotate/revoke at aistudio.google.com/apikey.
- Never commit `.env`. Never put passwords in the repo or chat tools.

## Commands (run from repo root)

```bash
# portal
.venv/Scripts/streamlit run src/facilityiq/portal/app.py
# regenerate 14-day telemetry lake
PYTHONPATH=src .venv/Scripts/python -m facilityiq.simulators.run_simulation
# retrain all 3 models + metrics
PYTHONPATH=src .venv/Scripts/python -m facilityiq.ml.train_all
# tests + coverage
.venv/Scripts/pytest --cov
# capture portal screenshots (Selenium)
.venv/Scripts/python scripts/capture_screens.py
# Azure teardown after final demo (deletes ONLY our storage account)
powershell scripts/azure_teardown.ps1
```

## Architecture at a glance

Simulators (HVAC/Energy/Occupancy) → unified schema validation → local JSONL
lake (+ Azure Blob copy) → feature windows (24h, trend slopes) → 3 ML models
(RF / IsolationForest / GBM, MLflow-tracked) → Streamlit portal (5 screens,
role-gated) + Gemini narratives + live Open-Meteo weather.

## Phase 2 remaining

IoT Hub live streaming (needs IT-created F1 hub), Functions routing, App
Service deploy (or Streamlit Cloud), Power BI ×3, Locust load test, Great
Expectations, full Selenium E2E suite.
