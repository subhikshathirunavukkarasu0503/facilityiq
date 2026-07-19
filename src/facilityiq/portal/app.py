"""FacilityIQ Management Portal — Streamlit.

Interactive portal with role-based access:
    viewer     -> Health Overview
    technician -> + Equipment Detail
    manager    -> + Maintenance Scheduling
    admin      -> + Admin panel

Live site weather from Open-Meteo (free, keyless) enriches HVAC context.

Run:  streamlit run src/facilityiq/portal/app.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

SRC = Path(__file__).resolve().parents[2]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from facilityiq.integrations.air_quality import (  # noqa: E402
    aqi_band, get_air_quality, ventilation_advice,
)
from facilityiq.integrations.melbourne_footfall import busiest, get_footfall  # noqa: E402
from facilityiq.integrations.weather import cooling_load_index, get_weather  # noqa: E402
from facilityiq.ml.features import load_domain  # noqa: E402
from facilityiq.ml.predict import explain_prediction, fleet_assessment  # noqa: E402
from facilityiq.portal.auth import (  # noqa: E402
    allowed_screens, authenticate, list_users,
)

st.set_page_config(page_title="FacilityIQ", page_icon="🏢", layout="wide")

STATUS_COLOR = {"green": "#21a366", "yellow": "#e6a817", "red": "#d64545"}
STATUS_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}

SCREEN_LABELS = {
    "overview": "🏢 Health Overview",
    "detail": "🔍 Equipment Detail",
    "maintenance": "🗓️ Maintenance Scheduling",
    "ai": "🤖 AI Predictive Intelligence",
    "admin": "⚙️ Admin",
}

# ---------------------------------------------------------------- styling --

_CSS = """
<style>
@keyframes gradientShift {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}
.stApp {
    background: linear-gradient(-45deg, #0f2027, #203a43, #2c5364, #1a2980);
    background-size: 400% 400%;
    animation: gradientShift 18s ease infinite;
}
[data-testid="stSidebar"] {
    background: rgba(10, 25, 41, 0.92);
    backdrop-filter: blur(8px);
}
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
h1, h2, h3, .stMarkdown p, .stMarkdown li, [data-testid="stMetricLabel"],
[data-testid="stMetricValue"], [data-testid="stWidgetLabel"] p {
    color: #e6edf3 !important;
}
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.07);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 14px 18px;
}
[data-testid="stMetricValue"] {
    font-size: 1.7rem !important;   /* keep values from truncating to "…" */
    white-space: nowrap;
}
/* Tabs: inactive labels were fading into the background */
button[data-baseweb="tab"] p,
button[data-baseweb="tab"] {
    color: rgba(230, 237, 243, 0.75) !important;
}
button[data-baseweb="tab"][aria-selected="true"] p {
    color: #5cc8ff !important;
    font-weight: 600;
}
button[data-baseweb="tab"]:hover p { color: #ffffff !important; }
/* Buttons (main + sidebar): solid, legible */
.stButton > button, [data-testid="stSidebar"] .stButton > button,
[data-testid="stFormSubmitButton"] > button {
    background: rgba(92, 200, 255, 0.16) !important;
    border: 1px solid rgba(92, 200, 255, 0.45) !important;
    color: #eaf6ff !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: rgba(92, 200, 255, 0.30) !important;
    border-color: #5cc8ff !important;
}
/* Radio + checkbox labels, captions, expanders */
[data-testid="stCaptionContainer"], .stRadio label p,
[data-testid="stExpander"] summary p {
    color: rgba(230, 237, 243, 0.85) !important;
}
/* Selectbox / multiselect text */
[data-baseweb="select"] * { color: #e6edf3 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 14px;
}
.fiq-badge {
    display: inline-block; padding: 2px 12px; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600; letter-spacing: 0.4px;
}
.fiq-login-card {
    background: rgba(255,255,255,0.07); backdrop-filter: blur(14px);
    border: 1px solid rgba(255,255,255,0.15); border-radius: 18px;
    padding: 2.2rem 2.5rem; margin-top: 4rem;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def role_badge(role: str) -> str:
    colors = {"admin": "#d64545", "manager": "#e6a817",
              "technician": "#4a90d9", "viewer": "#21a366"}
    return (f'<span class="fiq-badge" style="background:{colors[role]};'
            f'color:white">{role.upper()}</span>')


# ------------------------------------------------------------------- data --

@st.cache_resource(show_spinner="First run: generating telemetry lake…")
def ensure_data() -> bool:
    """Cloud cold-start safety: if the lake is absent (fresh container),
    regenerate 14 days of fleet telemetry (~15 s). Models ship in the repo."""
    lake = Path(__file__).resolve().parents[3] / "data" / "lake"
    if not any(lake.rglob("*.jsonl")) if lake.exists() else True:
        from facilityiq.ingestion.sinks import LocalLakeSink
        from facilityiq.simulators.devices import simulate_fleet

        # couple the regenerated telemetry to live Chennai weather
        bias = get_weather().temperature_c - 30.0
        sink = LocalLakeSink(lake)
        for msg in simulate_fleet(days=14.0, ambient_bias_c=bias):
            sink.write(msg)
    return True


@st.cache_data(ttl=120, show_spinner="Scoring fleet with ML models…")
def get_assessment() -> dict:
    ensure_data()
    return fleet_assessment()


@st.cache_data(ttl=300)
def get_raw(domain: str) -> pd.DataFrame:
    return load_domain(domain)


@st.cache_data(ttl=900, show_spinner=False)
def get_site_weather():
    return get_weather()


@st.cache_data(ttl=900, show_spinner=False)
def get_site_air_quality():
    return get_air_quality()


@st.cache_data(ttl=900, show_spinner=False)
def get_site_footfall():
    return get_footfall()


# ------------------------------------------------------------ components --

def gauge(value: float, title: str, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100,
        number={"suffix": "%", "font": {"color": "#e6edf3", "size": 26}},
        title={"text": title, "font": {"color": "#e6edf3", "size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#e6edf3"},
            "bar": {"color": color},
            "bgcolor": "rgba(255,255,255,0.08)",
            "steps": [
                {"range": [0, 35], "color": "rgba(33,163,102,0.25)"},
                {"range": [35, 65], "color": "rgba(230,168,23,0.25)"},
                {"range": [65, 100], "color": "rgba(214,69,69,0.25)"},
            ],
        },
    ))
    fig.update_layout(height=180, margin=dict(l=25, r=25, t=40, b=5),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig


def sparkline(series: pd.Series, color: str = "#5cc8ff") -> go.Figure:
    fig = go.Figure(go.Scatter(y=series, mode="lines",
                               line=dict(color=color, width=1.6),
                               fill="tozeroy",
                               fillcolor="rgba(92,200,255,0.12)"))
    fig.update_layout(height=60, margin=dict(l=0, r=0, t=0, b=0),
                      xaxis_visible=False, yaxis_visible=False,
                      showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)")
    return fig


def dark_fig(fig: go.Figure, height: int = 300) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.04)",
        font=dict(color="#e6edf3"), legend=dict(orientation="h"))
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    return fig


def weather_panel() -> None:
    w = get_site_weather()
    cli = cooling_load_index(w.temperature_c, w.humidity_pct)
    src = {"live": "🛰️ live · Open-Meteo", "cache": "🗂️ cached",
           "fallback": "⚠️ offline fallback"}[w.source]
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 2])
        c1.markdown(f"**Site weather — Chennai**  \n{w.condition} · {src}")
        c2.metric("Outdoor", f"{w.temperature_c:.1f} °C")
        c3.metric("Humidity", f"{w.humidity_pct:.0f} %")
        c4.metric("Feels like", f"{w.feels_like_c:.1f} °C")
        load_txt = "LOW" if cli < 0.33 else ("MODERATE" if cli < 0.66 else "HIGH")
        c5.metric("HVAC cooling load index", f"{cli:.0%}", delta=load_txt,
                  delta_color="off",
                  help="Derived from live outdoor temperature + humidity vs a "
                       "24 °C indoor setpoint. High outdoor load means degraded "
                       "compressors are under maximum stress — prioritize them.")

    aq = get_site_air_quality()
    aq_src = {"live": "🛰️ live · Open-Meteo Air Quality", "cache": "🗂️ cached",
              "fallback": "⚠️ offline fallback"}[aq.source]
    with st.container(border=True):
        a1, a2, a3, a4, a5 = st.columns([2, 1, 1, 1, 3])
        a1.markdown(f"**Outdoor air quality**  \n{aq_src}")
        a2.metric("AQI (EU)", f"{aq.aqi:.0f}", delta=aqi_band(aq.aqi),
                  delta_color="off")
        a3.metric("PM2.5", f"{aq.pm2_5:.0f} µg/m³")
        a4.metric("PM10", f"{aq.pm10:.0f} µg/m³")
        a5.markdown(f"**Ventilation recommendation**  \n{ventilation_advice(aq)}")


# --------------------------------------------------------------- screens --

def screen_overview(data: dict) -> None:
    st.title("🏢 Facility Health Overview")
    weather_panel()

    fleet = data["fleet"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Monitored assets", fleet["total_assets"])
    c2.metric("🟢 Healthy", fleet["status_counts"]["green"])
    c3.metric("🟡 Watch", fleet["status_counts"]["yellow"])
    c4.metric("🔴 Critical", fleet["status_counts"]["red"])

    tab_alerts, tab_fleet, tab_trends, tab_space = st.tabs(
        ["🚨 Active alerts", "📋 Fleet table", "📈 24h trends", "🪑 Space"])

    with tab_alerts:
        alerts = fleet["active_alerts"]
        acked = st.session_state.setdefault("acked_alerts", set())
        pending = [a for a in alerts if a["device_id"] not in acked]
        if not pending:
            st.success("No unacknowledged alerts. All equipment within "
                       "normal parameters.")
        for a in sorted(pending, key=lambda x: -x["failure_probability"]):
            with st.container(border=True):
                col1, col2, col3 = st.columns([4, 6, 2])
                col1.markdown(
                    f"{STATUS_EMOJI[a['status']]} **{a['device_id']}** "
                    f"({a['domain']})  \nFailure prob: "
                    f"**{a['failure_probability']:.0%}**")
                col2.markdown(explain_prediction(a))
                if col3.button("Acknowledge", key=f"ack-{a['device_id']}"):
                    acked.add(a["device_id"])
                    st.rerun()
        if acked:
            st.caption(f"Acknowledged this session: {', '.join(sorted(acked))}")
            if st.button("Reset acknowledgements"):
                acked.clear()
                st.rerun()

    with tab_fleet:
        rows = data["hvac"] + data["energy"]
        if rows:
            df = pd.DataFrame(rows)[
                ["device_id", "domain", "status", "failure_probability",
                 "days_to_maintenance"]]
            domains = st.multiselect(
                "Filter domain", sorted(df["domain"].unique()),
                default=sorted(df["domain"].unique()))
            df = df[df["domain"].isin(domains)]
            st.dataframe(
                df.sort_values("failure_probability", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "failure_probability": st.column_config.ProgressColumn(
                        "failure probability", min_value=0, max_value=1),
                })

    with tab_trends:
        hvac_raw = get_raw("hvac")
        if not hvac_raw.empty:
            recent = hvac_raw[hvac_raw["timestamp"] >=
                              hvac_raw["timestamp"].max() - pd.Timedelta("24h")]
            cols = st.columns(min(recent["device_id"].nunique(), 5))
            for col, (dev, g) in zip(cols, recent.groupby("device_id")):
                col.caption(dev)
                col.plotly_chart(sparkline(g["compressor_efficiency"]),
                                 use_container_width=True, key=f"spark-{dev}")
                col.caption(f"efficiency {g['compressor_efficiency'].iloc[-1]:.2f}")

    with tab_space:
        ff = get_site_footfall()
        ff_src = {"live": "🛰️ live · City of Melbourne open sensors",
                  "cache": "🗂️ cached", "fallback": "⚠️ offline fallback"}[ff.source]
        with st.container(border=True):
            st.markdown(f"**Live footfall — real pedestrian sensors** · {ff_src}")
            st.caption("Minute-level counts from the City of Melbourne "
                       "pedestrian counting system (physical sensors, free "
                       "open-data API) — demonstrates the pipeline running on "
                       "genuinely live occupancy telemetry.")
            top = busiest(ff, 5)
            cols = st.columns(len(top) or 1)
            for col, (lid, total) in zip(cols, top):
                col.metric(f"Sensor {lid}", f"{total}",
                           help="pedestrians counted in the covered window")
        occ = data["occupancy"]
        if occ:
            odf = pd.DataFrame(occ)
            col1, col2 = st.columns(2)
            fig = px.bar(odf, x="device_id", y="avg_desk_utilization",
                         title="Average desk utilization (work hours)",
                         color_discrete_sequence=["#5cc8ff"])
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            col1.plotly_chart(dark_fig(fig), use_container_width=True)
            fig2 = px.bar(odf, x="device_id", y="ghost_booking_rate",
                          title="Booked-but-empty (ghost booking) rate",
                          color_discrete_sequence=["#ff7b72"])
            fig2.update_yaxes(tickformat=".0%", range=[0, 1])
            col2.plotly_chart(dark_fig(fig2), use_container_width=True)


def screen_detail(data: dict) -> None:
    st.title("🔍 Equipment Detail")

    assets = {a["device_id"]: a for a in data["hvac"] + data["energy"]}
    if not assets:
        st.warning("No equipment data. Run the simulator first.")
        return
    device_id = st.selectbox("Select asset", sorted(assets))
    a = assets[device_id]

    g1, g2, g3 = st.columns(3)
    g1.plotly_chart(gauge(a["failure_probability"], "Failure probability",
                          STATUS_COLOR[a["status"]]),
                    use_container_width=True, key="gauge-main")
    if a["domain"] == "hvac":
        g2.plotly_chart(gauge(a["compressor_failure_prob"],
                              "Compressor model (RF)", "#5cc8ff"),
                        use_container_width=True, key="gauge-comp")
        g3.plotly_chart(gauge(a["motor_degradation_prob"],
                              "Motor model (GBM)", "#b48ead"),
                        use_container_width=True, key="gauge-motor")
    else:
        g2.metric("Anomaly right now",
                  "YES 🚨" if a.get("anomaly_now") else "no")
        g3.metric("Days to maintenance", a["days_to_maintenance"])

    st.info(explain_prediction(a))

    raw = get_raw(a["domain"])
    g = raw[raw["device_id"] == device_id].sort_values("timestamp")
    if g.empty:
        return

    span = st.radio("Window", ["24h", "3D", "7D", "all"], index=2,
                    horizontal=True)
    if span != "all":
        g = g[g["timestamp"] >= g["timestamp"].max() - pd.Timedelta(span)]

    if a["domain"] == "hvac":
        metric_sets = [
            ("Compressor efficiency", ["compressor_efficiency"]),
            ("Vibration (mm/s)", ["vibration_mm_s"]),
            ("Temperatures (°C)", ["supply_temp_c", "return_temp_c",
                                   "motor_temp_c"]),
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
        fig.update_layout(title=title)
        cols[i % 2].plotly_chart(dark_fig(fig), use_container_width=True,
                                 key=f"detail-{device_id}-{i}")

    if a["domain"] == "energy" and a.get("anomalies"):
        st.subheader("Anomaly timeline (Isolation Forest)")
        adf = pd.DataFrame(a["anomalies"])
        adf["window_end"] = pd.to_datetime(adf["window_end"])
        fig = px.scatter(adf, x="window_end", y="score",
                         color_discrete_sequence=["#ff7b72"])
        st.plotly_chart(dark_fig(fig, 260), use_container_width=True)


def screen_maintenance(data: dict) -> None:
    st.title("🗓️ Maintenance Scheduling")
    st.caption("AI-optimized recommendations ranked by urgency. "
               "Condition-based — driven by live model scores, not the calendar.")

    assets = sorted(data["hvac"] + data["energy"],
                    key=lambda a: -a["failure_probability"])
    weather = get_site_weather()
    cli = cooling_load_index(weather.temperature_c, weather.humidity_pct)

    LABOR_COST = {"hvac": 8500, "energy": 6000}       # ₹ per corrective visit
    FAILURE_COST = {"hvac": 95000, "energy": 140000}  # ₹ emergency breakdown

    rows = []
    today = datetime.now().date()
    for a in assets:
        p = a["failure_probability"]
        urgency = ("P1 — immediate" if p >= 0.85 else
                   "P2 — this week" if p >= 0.5 else
                   "P3 — next cycle" if p >= 0.35 else "P4 — routine")
        due = today + timedelta(days=int(a["days_to_maintenance"]))
        avoided = int(p * FAILURE_COST[a["domain"]] - LABOR_COST[a["domain"]])
        rows.append({
            "asset": a["device_id"], "domain": a["domain"],
            "urgency": urgency, "failure_prob": p,
            "due_by": due.isoformat(),
            "est_labor_₹": LABOR_COST[a["domain"]],
            "cost_avoidance_₹": max(avoided, 0),
        })
    df = pd.DataFrame(rows)

    c1, c2, c3 = st.columns(3)
    c1.metric("Work orders recommended",
              int((df["failure_prob"] >= 0.35).sum()))
    c2.metric("Projected cost avoidance",
              f"₹{int(df['cost_avoidance_₹'].sum()):,}")
    c3.metric("Outdoor cooling load", f"{cli:.0%}",
              help="High load = degraded HVAC assets face maximum stress; "
                   "P1/P2 HVAC work should not slip.")

    st.dataframe(
        df, use_container_width=True, hide_index=True,
        column_config={"failure_prob": st.column_config.ProgressColumn(
            "failure probability", min_value=0, max_value=1)})

    st.subheader("Generate work order")
    pick = st.selectbox("Asset", df[df["failure_prob"] >= 0.35]["asset"]
                        if (df["failure_prob"] >= 0.35).any() else df["asset"])
    sel = df[df["asset"] == pick].iloc[0]
    a = next(x for x in assets if x["device_id"] == pick)
    if st.button("📄 Create work order draft"):
        st.code(
            f"WORK ORDER (DRAFT)\n"
            f"Asset:        {sel['asset']} ({sel['domain']})\n"
            f"Priority:     {sel['urgency']}\n"
            f"Due by:       {sel['due_by']}\n"
            f"Failure prob: {sel['failure_prob']:.0%}\n"
            f"Est. labor:   ₹{sel['est_labor_₹']:,}\n"
            f"Rationale:    {explain_prediction(a)}\n",
            language=None)
        st.toast(f"Work order draft for {pick} ready", icon="📄")

    st.subheader("What-if: maintenance timing")
    delay = st.slider("Delay maintenance by (days)", 0, 21, 0)
    base = float(sel["failure_prob"])
    # crude compounding risk model for the demo: +6%/day relative growth
    risk = min(base * (1.06 ** delay), 1.0)
    st.progress(risk, text=f"Projected failure risk after {delay} day delay: "
                           f"{risk:.0%}")
    if risk >= 0.85 and base < 0.85:
        st.warning("Delay pushes this asset into P1 territory.")


def screen_ai(data: dict) -> None:
    st.title("🤖 AI Predictive Intelligence")
    from facilityiq.integrations.gemini import (
        api_key, asset_narrative, weekly_summary,
    )
    if not api_key():
        st.warning("GEMINI_API_KEY not configured — narratives fall back to "
                   "templates. Add the key to `.env`.")

    w = get_site_weather()
    weather_ctx = {"outdoor_temp_c": w.temperature_c,
                   "humidity_pct": w.humidity_pct, "condition": w.condition}
    src_badge = {"gemini": "🤖 Gemini", "cache": "🗂️ cached Gemini",
                 "template": "📋 template fallback"}

    st.subheader("Failure predictions — all 3 AI scenarios")
    scen1, scen2, scen3 = st.columns(3)
    hvac = data["hvac"]
    comp_top = max(hvac, key=lambda a: a["compressor_failure_prob"], default=None)
    motor_top = max(hvac, key=lambda a: a["motor_degradation_prob"], default=None)
    elec_top = max(data["energy"], key=lambda a: a["failure_probability"],
                   default=None)
    if comp_top:
        scen1.plotly_chart(
            gauge(comp_top["compressor_failure_prob"],
                  f"HVAC compressor · {comp_top['device_id']}", "#5cc8ff"),
            use_container_width=True, key="ai-g1")
    if elec_top:
        scen2.plotly_chart(
            gauge(elec_top["failure_probability"],
                  f"Electrical fault · {elec_top['device_id']}", "#e6a817"),
            use_container_width=True, key="ai-g2")
    if motor_top:
        scen3.plotly_chart(
            gauge(motor_top["motor_degradation_prob"],
                  f"Motor degradation · {motor_top['device_id']}", "#b48ead"),
            use_container_width=True, key="ai-g3")

    st.subheader("Ask the AI about an asset")
    assets = {a["device_id"]: a for a in data["hvac"] + data["energy"]}
    pick = st.selectbox("Asset", sorted(assets), key="ai-asset")
    a = assets[pick]
    if st.button("🧠 Generate AI explanation"):
        with st.spinner("Gemini analyzing model outputs…"):
            text, source = asset_narrative(
                a, weather=weather_ctx, fallback=explain_prediction(a))
        st.info(text)
        st.caption(f"Source: {src_badge[source]}")

    st.subheader("Weekly facility health summary")
    if st.button("📰 Generate weekly summary"):
        with st.spinner("Gemini writing the weekly summary…"):
            fallback = (
                f"{data['fleet']['status_counts']['red']} assets critical, "
                f"{data['fleet']['status_counts']['green']} healthy. "
                "Review active alerts and schedule P1 work first.")
            text, source = weekly_summary(data, fallback=fallback)
        st.markdown(text)
        st.caption(f"Source: {src_badge[source]}")

    st.subheader("Anomaly pattern dashboard")
    anom_rows = []
    for e in data["energy"]:
        for an in e.get("anomalies", []):
            anom_rows.append({"device": e["device_id"],
                              "window_end": an["window_end"],
                              "score": an["score"]})
    if anom_rows:
        adf = pd.DataFrame(anom_rows)
        adf["window_end"] = pd.to_datetime(adf["window_end"])
        fig = px.scatter(adf, x="window_end", y="score", color="device",
                         title="Detected anomalies across the energy fleet "
                               "(Isolation Forest)")
        st.plotly_chart(dark_fig(fig, 320), use_container_width=True)
    else:
        st.success("No anomalies flagged across the fleet.")


def screen_admin(data: dict) -> None:
    st.title("⚙️ Admin")
    st.subheader("Users & roles")
    st.dataframe(pd.DataFrame([u.__dict__ for u in list_users()]),
                 hide_index=True, use_container_width=True)

    st.subheader("System status")
    w = get_site_weather()
    lake = Path(__file__).resolve().parents[3] / "data" / "lake"
    n_files = len(list(lake.rglob("*.jsonl"))) if lake.exists() else 0
    models_dir = Path(__file__).resolve().parents[3] / "models"
    models = sorted(p.stem for p in models_dir.glob("*.joblib")) \
        if models_dir.exists() else []
    c1, c2, c3 = st.columns(3)
    c1.metric("Lake files", n_files)
    c2.metric("Trained models", len(models))
    c3.metric("Weather source", w.source)
    st.caption("Models: " + (", ".join(models) or "none"))

    if st.button("🧹 Clear portal caches"):
        st.cache_data.clear()
        st.toast("Caches cleared", icon="🧹")


# ----------------------------------------------------------------- login --

def login_gate() -> dict | None:
    user = st.session_state.get("user")
    if user:
        return user

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown('<div class="fiq-login-card">', unsafe_allow_html=True)
        st.markdown("## 🏢 FacilityIQ")
        st.caption("Smart Facility Management Platform — sign in")
        with st.form("login", clear_on_submit=False):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            u = authenticate(username, password)
            if u is None:
                time.sleep(0.6)  # slow trivial brute force
                st.error("Invalid credentials")
            else:
                st.session_state["user"] = u.__dict__
                st.rerun()
        with st.expander("Demo accounts"):
            st.markdown(
                "| user | password | role |\n|---|---|---|\n"
                "| viewer | viewer@123 | Executive viewer |\n"
                "| tech | tech@123 | Technician |\n"
                "| manager | manager@123 | Facilities manager |\n"
                "| admin | admin@123 | Administrator |")
        st.markdown("</div>", unsafe_allow_html=True)
    return None


def main() -> None:
    inject_css()
    user = login_gate()
    if not user:
        return

    st.sidebar.title("FacilityIQ")
    st.sidebar.markdown(
        f"{user['full_name']}  \n{role_badge(user['role'])}",
        unsafe_allow_html=True)
    st.sidebar.divider()

    screens = allowed_screens(user["role"])
    choice = st.sidebar.radio(
        "Screen", screens, format_func=lambda s: SCREEN_LABELS[s])

    st.sidebar.divider()
    if st.sidebar.button("🔄 Refresh data"):
        st.cache_data.clear()
    if st.sidebar.button("🚪 Sign out"):
        st.session_state.pop("user", None)
        st.session_state.pop("acked_alerts", None)
        st.rerun()
    st.sidebar.caption("Power BI dashboards + Azure deployment ship in Phase 2.")

    try:
        data = get_assessment()
    except FileNotFoundError:
        st.error("Models not trained yet. Run: "
                 "`python -m facilityiq.ml.train_all`")
        return

    {"overview": screen_overview, "detail": screen_detail,
     "maintenance": screen_maintenance, "ai": screen_ai,
     "admin": screen_admin}[choice](data)


main()
