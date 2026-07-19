# FacilityIQ — Mid-Term Report (Week 10 Deliverable)

**RFP:** S4-I-18 — Smart Facility Management Platform
**Participant:** Subhiksha Thirunavukkarasu (P399)
**Semester:** 4 — Integration Mastery (Capstone)

---

## 1. Mid-term scope vs. delivered

| Week 10 requirement (proposal §8) | Status |
|---|---|
| IoT Hub ingestion operational across 3 domains | ✅ Ingestion pipeline operational across HVAC, Energy, Occupancy (local lake + Azure IoT Hub sink; Azure resources provisioning in progress) |
| 3 ML models trained with accuracy metrics | ✅ Random Forest, Isolation Forest, Gradient Boosting — metrics below |
| Portal with 2 functional screens | ✅ Health Overview + Equipment Detail (Streamlit) |
| Initial AI predictions on sample data | ✅ Live failure probabilities, days-to-maintenance, plain-language explanations |
| All unit/integration tests passing | ✅ 34/34 passing, 85% coverage (target ≥80%) |
| Mid-term documentation on Moodle | ✅ This report + evidence pack |

## 2. What was built

### Layer 1 — IoT Data Ingestion
- **Unified telemetry schema** (`ingestion/schema.py`): one message shape for all
  domains; strict validation (required fields, domain whitelist, per-metric
  physical sanity ranges, timestamp format). Invalid messages rejected and
  counted, never landed.
- **Device simulators** (`simulators/devices.py`): 13-device fleet across
  3 domains. Devices run `healthy`, `degrading` (accelerating drift toward a
  configured failure point) or `faulty` (steady-state failed). Physics encoded:
  compressor-efficiency decay shrinks the supply/return ΔT; bearing wear raises
  vibration; clogging filters raise ΔP; electrical faults produce voltage sags,
  load spikes and rising THD; occupancy follows weekday office curves with
  ghost-booking behaviour.
- **Sinks** (`ingestion/sinks.py`): local JSONL data lake partitioned
  `domain/date/device.jsonl` (mirrors the Blob landing-zone layout), plus an
  Azure IoT Hub device-client sink activated by
  `IOTHUB_DEVICE_CONNECTION_STRING`.
- **Scale demonstrated:** 14,784 telemetry messages (14 simulated days,
  13 devices) ingested in 14.7 s, 0 rejects.

### Layer 2 — ML Analytics
- **Feature engineering** (`ml/features.py`): 24 h sliding windows, 6 h step;
  per-metric rolling mean/std/last + least-squares **trend slope** (degradation
  is a direction, not a level) + derived ΔT.
- **Training data** (`ml/datasets.py`): dedicated 28-day training fleets
  (separate from the demo fleet — models never see demo devices). Ground-truth
  labels from simulator degradation profiles; positive = failure within the
  7-day horizon **or already failed**.
- **Grouped train/test split by device** — no device appears in both sets, so
  metrics measure generalization to unseen equipment.

### Model results (held-out test set)

| Model | Algorithm | Precision | Recall | F1 | ROC-AUC | Target |
|---|---|---|---|---|---|---|
| HVAC compressor failure | Random Forest (300 trees) | 0.998 | 0.995 | **0.997** | 0.9999 | F1 > 0.85 ✅ |
| Motor/pump degradation | Gradient Boosting | 0.968 | 0.980 | **0.974** | 0.999 | F1 > 0.85 ✅ |
| Electrical fault detection | Isolation Forest (unsupervised) | 0.621 | **1.000** | 0.766 | 0.849 | anomaly detection rate > 0.90 ✅ |

Isolation Forest trains **unsupervised on healthy meters only**; labels are
used purely for evaluation. 100% of injected fault windows detected.
Confusion-matrix plots: `models/*_confusion.png`. Experiments tracked in
MLflow (`mlruns/`).

### Layer 3 — Management Portal (Streamlit)
- **Screen 1 — Facility Health Overview:** fleet KPI tiles (green/yellow/red),
  ranked active alerts with plain-language explanations, per-asset health table
  with failure-probability bars, 24 h efficiency sparklines, space-utilization
  and ghost-booking charts.
- **Screen 2 — Equipment Detail:** per-asset telemetry charts (efficiency,
  vibration, temperatures, filter ΔP / power, voltage, PF, THD), both model
  probabilities, days-to-maintenance estimate, anomaly timeline for meters.
- Explanations are currently template-based (the proposal's documented
  fallback); Gemini narrative generation is Phase 2 (Screen 4).

### Current live fleet assessment (demo data)

| Asset | Ground truth | Model verdict |
|---|---|---|
| hvac-ahu-01, hvac-chiller-01 | healthy | 🟢 p≈0.00 |
| hvac-ahu-02 (degrading) | failed day ~12.6 | 🔴 p=1.00 |
| hvac-chiller-02 (degrading) | failed day ~10.5 | 🔴 p=1.00 |
| hvac-pump-01 (faulty) | failed | 🔴 p=1.00 |
| meter-main-01, meter-floor2-01 | healthy | 🟢 |
| meter-floor1-01 (degrading) | fault developing | 🔴 p=0.84 |
| meter-server-01 (faulty) | faulty | 🔴 p=0.88 |

Zero false positives, zero missed failures on the demo fleet.

## 3. QA evidence

- **34 tests, all passing; 85% statement coverage** (`pytest --cov`).
- Unit: schema validation (9 cases), simulator physics + determinism (10),
  feature engineering (5).
- Integration: simulator → validation → partitioned lake (3);
  end-to-end simulate → ingest → featurize → score (1).
- Model quality gates *encoded as tests*: F1 ≥ 0.85 for both classifiers,
  anomaly recall ≥ 0.90, dataset label sanity.
- **CI:** GitHub Actions runs the full suite with `--cov-fail-under=80` on
  every push (`.github/workflows/ci.yml`).

### Defect found & fixed by the QA process
End-to-end test hardening exposed a real modeling defect: post-failure windows
of degrading training devices were labeled *healthy*, teaching the model that
steady-state degraded equipment (flat slopes) is fine — the faulty demo pump
scored p≈0.02. Fix: label post-failure windows positive and add steady-state
faulty devices to training fleets. Faulty pump now scores p=0.99. Documented as
evidence that layered QA catches ML logic errors, not just code errors.

## 4. Architecture (mid-term state)

```
Simulators (HVAC / Energy / Occupancy)
        │  unified schema + validation
        ▼
Sinks: Azure IoT Hub ──► (Functions ► Blob)   [Azure path]
       Local JSONL lake (Blob layout)         [dev path]
        ▼
Feature pipeline (24h windows, trend slopes)
        ▼
Models: RF · GBM · IsolationForest  (MLflow tracked)
        ▼
Streamlit portal (Screens 1–2)  ·  models/*_metrics.json
```

## 5. Phase 2 plan (Weeks 11–17)
1. Portal Screens 3 (Maintenance Scheduling) + 4 (AI Predictive Intelligence).
2. Gemini 2.5 Flash narrative generation replacing template explanations.
3. Azure deployment: IoT Hub + Functions + Blob + App Service (code paths
   already built; needs subscription provisioning).
4. Power BI dashboards ×3 from exported analytics datasets.
5. Selenium E2E scenarios, Great Expectations data-quality suite, Locust load
   test at 10K+ records, full regression.

## 6. Budget status
Spend to date: **₹0** (all local + open-source). Azure free tiers and Gemini
free tier remain available for Phase 2. Ceiling ₹2,500 untouched.
