# FacilityIQ — Presentation Prep Guide

Read this top-to-bottom once and you can explain every screen, every number,
and every design decision. Written for the Week-10 mid-term review.

---

## 1. Elevator pitch (30 seconds)

"FacilityIQ turns raw building-sensor telemetry into maintenance decisions.
Simulated IoT devices for three domains — HVAC, energy, occupancy — stream
validated telemetry into a data lake. Three machine-learning models score
every asset continuously: a Random Forest predicts compressor failures 5–14
days ahead, an Isolation Forest catches electrical anomalies unsupervised, and
a Gradient Boosting model tracks motor wear. A role-gated web portal shows
fleet health, explains every prediction in plain language via Gemini, and
generates ranked work orders with cost-avoidance estimates. Four live free
APIs feed real-world context: weather, air quality, city footfall sensors, and
Gemini. Built entirely on free tiers — ₹0 spent of the ₹2,500 budget."

---

## 2. End-to-end data flow (the one diagram to memorize)

```
[13 simulated devices]        [4 REAL live APIs]
 HVAC×5 Energy×4 Occ×4         Open-Meteo weather ─┐
        │                      Open-Meteo air qual ─┤
        ▼                      Melbourne footfall ──┤→ portal panels
 unified schema check          Gemini narratives  ──┘   (fetched live,
 (reject bad messages)                                  cached 15 min)
        │
        ▼
 DATA LAKE (JSONL files)
 local: data/lake/…            mirrored → Azure Blob Storage
 layout: domain/date/device    container 'telemetry', 196 blobs
        │
        ▼
 FEATURE PIPELINE (pandas)
 24-hour sliding windows, 6-hour step
 per metric: mean, std, LAST value, TREND SLOPE
        │
        ▼
 3 ML MODELS (scikit-learn, tracked in MLflow)
 RF compressor · IsolationForest electrical · GBM motor
        │
        ▼
 STREAMLIT PORTAL (5 screens, role-gated login)
 every number computed on page load — nothing hardcoded
```

---

## 3. Screen-by-screen: where every piece of content comes from

### Login screen
- Credential check against salted SHA-256 hashes in `portal/auth.py`.
- 4 roles → different screens (viewer < technician < manager < admin).
- Say: "POC credential store; production swaps this one module for Azure AD."

### Screen 1 — Facility Health Overview
| Element | Source |
|---|---|
| Weather panel (33°C, thunderstorm…) | LIVE Open-Meteo API call, cached 15 min |
| HVAC cooling-load index | Formula on live temp+humidity vs 24°C setpoint |
| Air-quality panel + ventilation advice | LIVE Open-Meteo Air Quality API |
| KPI tiles (9 assets, 3🟢 1🟡 5🔴) | Models score latest 24h window per device, thresholds: <35% green, <65% yellow, else red |
| Active alerts + explanations | Every non-green asset; explanation text from template engine (deterministic), Gemini versions on Screen 4 |
| Sparklines | Last 24h of raw compressor-efficiency telemetry from the lake |
| Space tab: live footfall | LIVE City of Melbourne pedestrian sensor API (35 real sensors) |
| Desk utilization / ghost bookings | Computed from simulated occupancy telemetry (work-hours filter) |

### Screen 2 — Equipment Detail
- Asset picker → filters the lake to that device.
- Gauges = the two model probabilities for that asset (compressor RF, motor GBM)
  or anomaly score (energy assets).
- Telemetry charts = raw lake data, window selectable 24h/3D/7D/all.
- Anomaly timeline (energy) = every window the Isolation Forest flagged.

### Screen 3 — Maintenance Scheduling (manager+)
- Table = all assets ranked by failure probability → priority P1–P4.
- Due date = today + days-to-maintenance (heuristic mapping from probability).
- Cost avoidance = probability × emergency-breakdown cost − planned-labor cost
  (₹95K HVAC / ₹140K electrical breakdown estimates — state they're
  illustrative planning constants).
- Work-order generator = fills a draft from the live assessment.
- What-if slider = compounds risk +6%/day of delay (demo heuristic).

### Screen 4 — AI Predictive Intelligence (technician+)
- 3 gauges = worst asset per failure scenario (the RFP's 3 required scenarios).
- "Generate AI explanation" = REAL Gemini API call: model outputs + live
  weather go into the prompt; answer labelled with source (Gemini / cached /
  template fallback).
- Weekly summary = Gemini writes from the full fleet assessment JSON.
- Responses disk-cached → demo can't die on quota/network (show the label).

### Admin screen (admin only)
- User registry (no password hashes exposed), lake file count, model list,
  weather-source health, cache controls.

---

## 4. How Azure storage works here (likely question)

- **Blob Storage, not Table Storage.** Blobs = files in the cloud. Our
  telemetry is JSONL files (one JSON message per line), organized
  `telemetry/<domain>/<date>/<device>.jsonl` — 196 blobs, ~5 MB.
- Why blobs and not tables/SQL: this is the **data-lake pattern** — raw,
  append-only sensor archives stored cheap, schema applied on read. Any
  downstream tool (Databricks, Power BI, Synapse) can consume the files
  directly. Azure Table Storage is a key-value row store — wrong shape for
  bulk time-series archives.
- Account `fiqlake28091`, resource group `rg-pSiddhi3.0-2026-01-sem4-Subhiksha`
  (company-assigned), region eastus, Standard_LRS (<₹5/month).
- Path to full Azure ingestion: simulators already have an IoT Hub client
  (`ingestion/sinks.py: IoTHubSink`); once IT creates the free F1 IoT Hub the
  flow becomes device → IoT Hub → routing → this same Blob container. Blocked
  only by corporate RBAC (I hold IoT Hub *Data* Contributor, not create
  rights) — this was proposal risk #3 and the approved fallback (direct Blob)
  is what runs today.

## 5. Where everything is stored (summary)

| Artefact | Location |
|---|---|
| Code, tests, docs, screenshots | GitHub (private) + local clone |
| Telemetry lake | Local `data/lake` + Azure Blob copy + committed to repo (cloud app self-contained) |
| Trained models (.joblib) | Repo `models/` (+ metrics JSON + confusion PNGs) |
| Experiment history | MLflow local `mlruns/` |
| Gemini API key | `.env` local (gitignored) + Streamlit Cloud secrets |
| Running app | Streamlit Community Cloud + localhost |

---

## 6. The ML story (the part they'll probe deepest)

1. **Training data is separate from the demo fleet.** Dedicated 28-day
   training simulations with ~30 devices per model; demo devices never seen in
   training. Grouped train/test split BY DEVICE — no leakage.
2. **Labels come from simulator ground truth**: a window is positive if the
   device fails within 7 days after it — or has already failed.
3. **Features are trends, not just levels**: per-metric rolling mean, std,
   last value, and least-squares slope over 24h windows. Degradation is a
   *direction*.
4. **Results (held-out):** HVAC RF F1 0.997 (ROC-AUC 0.9999) · Motor GBM F1
   0.974 · Electrical Isolation Forest recall 1.00 (trained unsupervised on
   healthy meters only; labels used only to evaluate).
5. **The QA war story (tell this — it's your best moment):** early on, the
   faulty demo pump scored 2% failure probability. Root cause: post-failure
   windows in training were labeled "healthy," so the model learned that
   steady degraded state with flat slopes = fine. Fix: label post-failure
   windows positive + add steady-state faulty devices to training. Pump went
   to 99%. Lesson: layered QA catches ML *logic* errors, not just code bugs —
   and an accuracy metric alone (F1 was already 0.92!) can hide them.

## 7. QA numbers (all measured, not estimated)

- **89 tests** across unit / integration / model-quality / UI (AppTest) /
  live-API mocks. **88% statement coverage** (pytest-cov).
- CI: GitHub Actions runs everything on every push with a hard
  `--cov-fail-under=80` gate. All green.
- Model quality bars are *encoded as tests*: F1≥0.85, anomaly recall≥0.90 —
  the suite fails if a retrain regresses.
- Selenium drives the real portal headless (login → all 5 screens); the
  screenshots in the submission doc were produced by that script.

## 8. Budget (they will ask)

- Spent: **₹0** of ₹2,500. Everything free tier. Storage <₹5/month, teardown
  script in repo deletes it after the final demo.
- Gemini stays free-tier because responses are cached; ₹400 provision intact.

## 9. Live demo script (8 minutes)

1. Open cloud URL → login screen. Log in as **viewer** → show they only get
   Screen 1. Sign out, log in as **admin**. (RBAC in 30 seconds.)
2. Screen 1: point at LIVE weather + air quality ("fetched seconds ago"),
   KPI tiles, read one alert explanation aloud.
3. Space tab: live Melbourne footfall — "35 real physical sensors, minute
   data, free government API."
4. Screen 2: pick `hvac-chiller-02` → show efficiency collapsing + vibration
   rising in the charts, gauges at 100%. "The model saw this trend days ago."
   Then pick `hvac-ahu-01` (healthy, 0%) for contrast.
5. Screen 3: ranked work orders, generate one, drag the what-if slider.
6. Screen 4: click "Generate AI explanation" → live Gemini, point at the
   source label. Generate the weekly summary.
7. Close with the QA war story (§6.5) + CI green + ₹0 budget.

**Demo insurance:** local portal (`localhost:8501`) is the backup if venue
network is bad; Gemini falls back to cache/templates automatically; weather
falls back to cache. Nothing in the demo has a single point of failure.

## 10. Likely tough questions — answers

- **"Is the sensor data real?"** — Sensors are simulated per the approved
  proposal (public live APIs for building HVAC internals don't exist — that
  data is physically private). But all ambient context is real: live weather,
  live air quality, live city footfall — and the simulation's ambient
  temperature is driven by the live weather feed.
- **"Why isn't IoT Hub connected?"** — Corporate RBAC (Data Contributor only).
  IT request raised; client code built and tested; approved fallback running.
- **"Why not Databricks?"** — 15K records don't need Spark; avoided
  Community-cluster timeout risk (proposal risk #5). Disclosed in Section 8
  of the submission.
- **"Would the models work on real equipment?"** — The pipeline would;
  the models would need retraining on that equipment's history. The
  architecture (windows → trend features → per-asset scoring) transfers as-is.
- **"What's Phase 2?"** — IoT Hub streaming, Functions alert routing, Power BI
  ×3, 10K-record load test (Locust), Great Expectations data-quality suite,
  full Selenium E2E, final docs.
