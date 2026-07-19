# FacilityIQ — Smart Facility Management Platform

End-to-end smart facility management platform: IoT sensor ingestion, ML-driven
failure prediction, anomaly detection, and a real-time management portal.

Response to RFP **S4-I-18** — Semester 4 Capstone (Integration Mastery).

## Architecture

```
[IoT Simulators] --> [Ingestion (Azure IoT Hub / local)] --> [Data Lake (Blob / local)]
                                                                  |
                                                          [Feature Pipeline]
                                                                  |
                                              [ML Models: RF / IsolationForest / GBM]
                                                                  |
                                     [Management Portal (Streamlit)] + [Power BI datasets]
```

## Domains

| Domain | Sensors |
|---|---|
| HVAC / Equipment | supply/return temp, humidity, compressor efficiency, vibration, filter ΔP |
| Energy | power draw, voltage, current, power factor, THD |
| Space / Occupancy | zone occupancy counts, meeting-room usage, desk utilization |

## ML Models (mid-term scope)

1. **HVAC Compressor Failure** — Random Forest classifier on efficiency-degradation and temperature-differential features. Predicts failure 5–14 days ahead.
2. **Electrical Fault Detection** — Isolation Forest anomaly detection on power-quality metrics (sags, THD, load imbalance).
3. **Motor/Pump Degradation** — Gradient Boosting on vibration spectral-band features and temperature trends.

Plus an unsupervised anomaly pipeline (Isolation Forest + Local Outlier Factor)
across all sensor streams.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt

# 1. Generate telemetry (all 3 domains, includes degradation + failure scenarios)
.venv/Scripts/python -m facilityiq.simulators.run_simulation

# 2. Train all models + write accuracy reports
.venv/Scripts/python -m facilityiq.ml.train_all

# 3. Launch management portal
.venv/Scripts/streamlit run src/facilityiq/portal/app.py

# 4. Run tests
.venv/Scripts/pytest
```

## Azure deployment

Set `IOTHUB_DEVICE_CONNECTION_STRING` to stream simulator telemetry into Azure
IoT Hub instead of the local lake. See `docs/azure_setup.md`.

## Repo layout

```
src/facilityiq/
  simulators/   IoT device simulators (HVAC, Energy, Occupancy)
  ingestion/    telemetry schema, validation, routing, sinks (local + IoT Hub)
  ml/           feature engineering, model training, prediction service
  portal/       Streamlit management portal
tests/          unit + integration tests (pytest)
data/           generated telemetry lake + training data
models/         trained models + accuracy metrics
docs/           mid-term documentation
```
