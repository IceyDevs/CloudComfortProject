"""
dashboard.py — CloudComfort Streamlit Dashboard
Run with:  streamlit run dashboard.py

Requires:
    pip install streamlit boto3 pandas
    AWS credentials configured (env vars, ~/.aws/credentials, or IAM role)
"""

from decimal import Decimal

import boto3
import pandas as pd
import streamlit as st
from boto3.dynamodb.conditions import Key
from datetime import datetime, timezone, timedelta
from streamlit_autorefresh import st_autorefresh

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CloudComfort Dashboard",
    page_icon="🌡️",
    layout="wide",
)

# ── DynamoDB setup ────────────────────────────────────────────────────────────

@st.cache_resource
def get_table():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"],
        aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
    )
    return dynamodb.Table("CloudComfortTable")

# ── Helpers ───────────────────────────────────────────────────────────────────

def decimal_to_float(obj):
    """
    Recursively convert Decimal → float in a dict/list.
    boto3 returns Decimals from DynamoDB; pandas and Streamlit expect floats.
    Without this, you get TypeError crashes when rendering charts.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj

def fetch_room_data(room_id: str, limit: int = 100) -> pd.DataFrame:
    try:
        table = get_table()  # ← this line added
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

        resp = table.query(
            KeyConditionExpression=Key("room_id").eq(room_id) & Key("timestamp").gte(cutoff),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = resp.get("Items", [])
        if not items:
            return pd.DataFrame()

        items = [decimal_to_float(item) for item in items]
        df = pd.DataFrame(items)
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        df = df.sort_values("timestamp")
        return df

    except Exception as e:
        st.error(f"DynamoDB query failed: {e}")
        return pd.DataFrame()

def ci_colour(ci: float) -> str:
    if ci >= 85:  return "🟢"
    if ci >= 70:  return "🟡"
    if ci >= 55:  return "🟠"
    return "🔴"

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Settings")
room = st.sidebar.selectbox("Room", ["CR101", "CR102", "CR103", "CR104", "CR105", "CR106", "CR107", "CR108", "CR109", "CR110"])
limit = st.sidebar.slider("Readings to show", 10, 200, 60)
refresh_secs = st.sidebar.slider("Auto-refresh (seconds)", 5, 60, 10)

# ── Main layout ───────────────────────────────────────────────────────────────

st.title("🌡️ CloudComfort Analytics Dashboard")
st.caption(f"Room: **{room}** · Last {limit} readings · Auto-refresh every {refresh_secs}s")

# Auto-refresh every N seconds
st_autorefresh(interval=refresh_secs * 1000, key="refresh")

df = fetch_room_data(room, limit)

if df.empty:
    st.info("No data yet for this room. Start the simulator and check back soon.")
else:
    latest = df.iloc[-1]
    ci_val = float(latest.get("ci", 0))
    ci_lbl = latest.get("ci_label", "—")
    icon   = ci_colour(ci_val)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Comfort Index", f"{icon} {ci_val:.1f}")
    col2.metric("Temperature",   f"{float(latest.get('temperature', 0)):.1f} °C")
    col3.metric("Humidity",      f"{float(latest.get('humidity', 0)):.1f} %")
    col4.metric("CO₂",           f"{int(latest.get('co2', 0))} ppm")
    col5.metric("Light",         f"{int(latest.get('light', 0))} lux")
    col6.metric("Noise",         f"{float(latest.get('noise', 0)):.1f} dB")

    if ci_val < 50:
        st.error(f"🚨 **COMFORT ALERT** — CI = {ci_val:.1f} ({ci_lbl}). Conditions are Critical.")
    elif ci_val < 70:
        st.warning(f"⚠️ CI = {ci_val:.1f} ({ci_lbl}). Conditions are below optimal.")

    st.divider()
    st.subheader("Comfort Index over time")
    st.line_chart(df.set_index("timestamp")["ci"])

    st.subheader("Sensor readings")
    sensor_cols = ["temperature", "humidity", "co2", "light", "noise"]
    available   = [c for c in sensor_cols if c in df.columns]
    if available:
        tabs = st.tabs([c.capitalize() for c in available])
        for tab, col in zip(tabs, available):
            with tab:
                st.line_chart(df.set_index("timestamp")[col])

    with st.expander("📋 Raw data"):
        st.dataframe(df.sort_values("timestamp", ascending=False), use_container_width=True)
