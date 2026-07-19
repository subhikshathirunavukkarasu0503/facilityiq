"""FacilityIQ Management Portal — Streamlit.

Mid-term scope: Screen 1 (Facility Health Overview) and Screen 2 (Equipment
Detail). Screens 3-4 land in Phase 2.

Run:  streamlit run src/facilityiq/portal/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from facilityiq.ml.features import load_domain  # noqa: E402
from facilityiq.ml.predict import explain_prediction, fleet_assessment  # noqa: E402

st.set_page_config(page_title="FacilityIQ", page_icon="🏢", layout="wide")

STATUS_COLOR = {"green": "#21a366", "yellow": "#e6a817", "red": "#d64545"}
STATUS_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}


@st.cache_data(ttl=120)
def get_assessment() -> dict:
    return fleet_assessment()


@st.cache_data(ttl=300)
def get_raw(domain: str) -> pd.DataFrame:
    return load_domain(domain)


def sparkline(series: pd.Series, color: str = "#4a90d9") -> go.Figure:
    fig = go.Figure(go.Scatter(y=series, mode="lines",
                               line=dict(color=color, width=1.5)))
    fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0),
                      xaxis_visible=False, yaxis_visible=False,
                      showlegend=False)
    return fig


def screen_health_overview(data: dict) -> None:
    st.title("🏢 Facility Health Overview")

    fleet = data["fleet"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monitored assets", fleet["total_assets"])
    c2.metric("🟢 Healthy", fleet["status_counts"]["green"])
    c3.metric("🟡 Watch", fleet["status_counts"]["yellow"])
    c4.metric("🔴 Critical", fleet["status_counts"]["red"])

    st.subheader("Active alerts")
    alerts = fleet["active_alerts"]
    if not alerts:
        st.success("No active alerts. All equipment within normal parameters.")
    for a in sorted(alerts, key=lambda x: -x["failure_probability"]):
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 2, 5])
            col1.markdown(f"{STATUS_EMOJI[a['status']]} **{a['device_id']}** "
                          f"({a['domain']})")
            col2.markdown(f"Failure prob: **{a['failure_probability']:.0%}**")
            col3.markdown(explain_prediction(a))

    st.subheader("Equipment health")
    rows = data["hvac"] + data["energy"]
    if rows:
        df = pd.DataFrame(rows)[
            ["device_id", "domain", "status", "failure_probability",
             "days_to_maintenance"]]
        df = df.sort_values("failure_probability", ascending=False)
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={
                "failure_probability": st.column_config.ProgressColumn(
                    "failure probability", min_value=0, max_value=1),
            })

    st.subheader("24-hour trends (critical metrics)")
    hvac_raw = get_raw("hvac")
    if not hvac_raw.empty:
        recent = hvac_raw[hvac_raw["timestamp"] >=
                          hvac_raw["timestamp"].max() - pd.Timedelta("24h")]
        cols = st.columns(min(len(recent["device_id"].unique()), 5))
        for col, (dev, g) in zip(cols, recent.groupby("device_id")):
            col.caption(dev)
            col.plotly_chart(sparkline(g["compressor_efficiency"]),
                             use_container_width=True,
                             key=f"spark-{dev}")
            col.caption(f"efficiency {g['compressor_efficiency'].iloc[-1]:.2f}")

    st.subheader("Space utilization snapshot")
    occ = data["occupancy"]
    if occ:
        odf = pd.DataFrame(occ)
        col1, col2 = st.columns(2)
        fig = px.bar(odf, x="device_id", y="avg_desk_utilization",
                     title="Average desk utilization (work hours)",
                     color_discrete_sequence=["#4a90d9"])
        fig.update_yaxes(tickformat=".0%", range=[0, 1])
        col1.plotly_chart(fig, use_container_width=True)
        fig2 = px.bar(odf, x="device_id", y="ghost_booking_rate",
                      title="Booked-but-empty (ghost booking) rate",
                      color_discrete_sequence=["#d64545"])
        fig2.update_yaxes(tickformat=".0%", range=[0, 1])
        col2.plotly_chart(fig2, use_container_width=True)


def screen_equipment_detail(data: dict) -> None:
    st.title("🔍 Equipment Detail")

    assets = {a["device_id"]: a for a in data["hvac"] + data["energy"]}
    if not assets:
        st.warning("No equipment data. Run the simulator first.")
        return
    device_id = st.selectbox("Select asset", sorted(assets))
    a = assets[device_id]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", f"{STATUS_EMOJI[a['status']]} {a['status'].upper()}")
    c2.metric("Failure probability", f"{a['failure_probability']:.0%}")
    c3.metric("Days to maintenance", a["days_to_maintenance"])
    c4.metric("Domain", a["domain"].upper())

    st.info(explain_prediction(a))

    raw = get_raw(a["domain"])
    g = raw[raw["device_id"] == device_id].sort_values("timestamp")
    if g.empty:
        return

    if a["domain"] == "hvac":
        metric_sets = [
            ("Compressor efficiency", ["compressor_efficiency"]),
            ("Vibration (mm/s)", ["vibration_mm_s"]),
            ("Temperatures (°C)", ["supply_temp_c", "return_temp_c", "motor_temp_c"]),
            ("Filter ΔP (Pa)", ["filter_dp_pa"]),
        ]
    else:
        metric_sets = [
            ("Power (kW)", ["power_kw"]),
            ("Voltage (V)", ["voltage_v"]),
            ("Power factor", ["power_factor"]),
            ("THD (%)", ["thd_pct"]),
        ]

    cols = st.columns(2)
    for i, (title, metrics) in enumerate(metric_sets):
        fig = go.Figure()
        for m in metrics:
            fig.add_trace(go.Scatter(x=g["timestamp"], y=g[m],
                                     mode="lines", name=m))
        fig.update_layout(title=title, height=300,
                          margin=dict(l=10, r=10, t=40, b=10),
                          legend=dict(orientation="h"))
        cols[i % 2].plotly_chart(fig, use_container_width=True,
                                 key=f"detail-{device_id}-{i}")

    if a["domain"] == "hvac":
        st.subheader("Model predictions")
        p1, p2 = st.columns(2)
        p1.metric("Compressor failure model (Random Forest)",
                  f"{a['compressor_failure_prob']:.0%}")
        p2.metric("Motor degradation model (Gradient Boosting)",
                  f"{a['motor_degradation_prob']:.0%}")

    if a["domain"] == "energy" and a.get("anomalies"):
        st.subheader("Anomaly timeline (Isolation Forest)")
        adf = pd.DataFrame(a["anomalies"])
        adf["window_end"] = pd.to_datetime(adf["window_end"])
        fig = px.scatter(adf, x="window_end", y="score",
                         title="Detected anomalies",
                         color_discrete_sequence=["#d64545"])
        st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.sidebar.title("FacilityIQ")
    st.sidebar.caption("Smart Facility Management Platform")
    screen = st.sidebar.radio("Screen", [
        "1 · Facility Health Overview",
        "2 · Equipment Detail",
    ])
    st.sidebar.divider()
    if st.sidebar.button("🔄 Refresh data"):
        st.cache_data.clear()
    st.sidebar.caption("Screens 3 (Maintenance Scheduling) and "
                       "4 (AI Predictive Intelligence) ship in Phase 2.")

    try:
        data = get_assessment()
    except FileNotFoundError:
        st.error("Models not trained yet. Run: "
                 "`python -m facilityiq.ml.train_all`")
        return

    if screen.startswith("1"):
        screen_health_overview(data)
    else:
        screen_equipment_detail(data)


main()
