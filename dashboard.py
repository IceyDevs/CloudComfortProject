"""
dashboard.py — CloudComfort Streamlit Dashboard
Run with:  streamlit run dashboard.py

Requires:
    pip install streamlit boto3 pandas streamlit-autorefresh
    AWS credentials configured (env vars, ~/.aws/credentials, or IAM role)
"""

from decimal import Decimal
from datetime import datetime, timezone, timedelta

import boto3
import pandas as pd
import streamlit as st
from boto3.dynamodb.conditions import Key
from streamlit_autorefresh import st_autorefresh

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CloudComfort Dashboard",
    page_icon="🌡️",
    layout="wide",
)

# ── AWS setup ─────────────────────────────────────────────────────────────────

@st.cache_resource
def get_table():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"],
        aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
    )
    return dynamodb.Table("CloudComfortTable")

@st.cache_resource
def get_lambda_client():
    return boto3.client(
        "lambda",
        region_name=st.secrets["aws"]["AWS_DEFAULT_REGION"],
        aws_access_key_id=st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj

def fetch_room_data(room_id: str, limit: int = 100) -> pd.DataFrame:
    try:
        table  = get_table()
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()

        resp  = table.query(
            KeyConditionExpression=Key("room_id").eq(room_id) & Key("timestamp").gte(cutoff),
            ScanIndexForward=False,
            Limit=limit,
        )
        items = resp.get("Items", [])
        if not items:
            return pd.DataFrame()

        items = [decimal_to_float(item) for item in items]
        df    = pd.DataFrame(items)
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="ISO8601")
        df = df.sort_values("timestamp")
        return df

    except Exception as e:
        st.error(f"DynamoDB query failed: {e}")
        return pd.DataFrame()

def ci_colour(ci: float) -> str:
    if ci >= 85: return "🟢"
    if ci >= 70: return "🟡"
    if ci >= 55: return "🟠"
    return "🔴"

def call_control(action: str) -> dict:
    import json
    try:
        client = get_lambda_client()
        response = client.invoke(
            FunctionName="CloudComfortSimulatorControl",
            InvocationType="RequestResponse",
            Payload=json.dumps({"body": json.dumps({"action": action})}),
        )

        if "FunctionError" in response:
            raw = json.loads(response["Payload"].read())
            return {"error": raw.get("errorMessage", "Lambda function error")}

        payload = json.loads(response["Payload"].read())

        # Unwrap API Gateway-style response
        body = payload.get("body", "{}")

        # Keep parsing until we have a dict (handles double/triple encoding)
        for _ in range(3):
            if isinstance(body, dict):
                return body
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    return {"error": f"Could not parse body: {body}"}
        
        return {"error": f"Unexpected body type after parsing: {type(body).__name__}"}

    except Exception as e:
        return {"error": str(e)}

def get_simulator_status() -> str:
    result = call_control("status")
    if not isinstance(result, dict):
        st.sidebar.warning(f"Unexpected response type: {type(result).__name__} — {result}")
        return "stopped"
    if "error" in result:
        st.sidebar.warning(f"Status check failed: {result['error']}")
        return "stopped"
    return result.get("status", "stopped")

# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ Settings")
room         = st.sidebar.selectbox("Room", [f"CR{100+i}" for i in range(1, 11)])
limit        = st.sidebar.slider("Readings to show", 10, 200, 60)
refresh_secs = st.sidebar.slider("Auto-refresh (seconds)", 5, 60, 10)

st.sidebar.divider()

# ── Simulator control ─────────────────────────────────────────────────────────

st.sidebar.subheader("🎛️ Simulator Control")

status = get_simulator_status()

if status == "running":
    st.sidebar.success("🟢 Simulator is Running")
    if st.sidebar.button("⏹ Stop Simulator", use_container_width=True):
        result = call_control("stop")
        if "error" in result:
            st.sidebar.error(f"Failed to stop: {result['error']}")
        else:
            st.sidebar.info("Simulator stopped.")
            st.rerun()
else:
    st.sidebar.error("🔴 Simulator is Stopped")
    if st.sidebar.button("▶ Start Simulator", use_container_width=True):
        result = call_control("start")
        if "error" in result:
            st.sidebar.error(f"Failed to start: {result['error']}")
        else:
            st.sidebar.info("Simulator started! Data will appear within 5 minutes.")
            st.rerun()

# ── Main layout ───────────────────────────────────────────────────────────────

st.title("🌡️ CloudComfort Analytics Dashboard")
st.caption(f"Room: **{room}** · Last {limit} readings · Auto-refresh every {refresh_secs}s")

st_autorefresh(interval=refresh_secs * 1000, key="refresh")

df = fetch_room_data(room, limit)
st.write("DEBUG — rows fetched:", len(df))
if not df.empty:
    st.write("Latest timestamp:", df["timestamp"].max())
    st.write("Earliest timestamp:", df["timestamp"].min())
    
#if df.empty:
#   st.info("No data yet for this room. Start the simulator and check back soon.")
#else:
#    latest = df.iloc[-1]
#    ci_val = float(latest.get("ci", 0))
#    ci_lbl = latest.get("ci_label", "—")
#    icon   = ci_colour(ci_val)*

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
