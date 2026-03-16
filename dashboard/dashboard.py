"""
CyberThreat AI Dashboard
Fully Structured Working Version
"""

import time
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import streamlit.components.v1 as components
from datetime import datetime

# ───────────────── CONFIG ─────────────────
API_BASE = "https://cyberthreat-api.onrender.com"
REFRESH_SECS = 5
HISTORY_LIMIT = 100

ATTACK_COLORS = {
    "Other": "#ec4899",
    "DDoS": "#ef4444",
    "Botnet": "#22c55e",
    "Port Scan": "#f97316",
    "Brute Force": "#3b82f6",
}

# ───────── PAGE CONFIG ─────────
st.set_page_config(
    page_title="CyberThreat Dashboard",
    page_icon="🛡️",
    layout="wide"
)

st.success("AI Model: Random Forest + Isolation Forest | Real-time Threat Detection")
st.info("AI Cyber Threat Detection using Random Forest + Isolation Forest trained on network traffic patterns.")

# ───────── SESSION STATE ─────────
if "blocked_ips" not in st.session_state:
    st.session_state.blocked_ips = set()

if "alerted_ids" not in st.session_state:
    st.session_state.alerted_ids = set()

if "alert_log" not in st.session_state:
    st.session_state.alert_log = []

if "sound_enabled" not in st.session_state:
    st.session_state.sound_enabled = True


# ───────── ALERT SOUND SCRIPT ─────────
ALERT_SOUND = """
<script>
var audioCtx = new (window.AudioContext || window.webkitAudioContext)();
function playSound(){
var oscillator = audioCtx.createOscillator();
var gainNode = audioCtx.createGain();
oscillator.connect(gainNode);
gainNode.connect(audioCtx.destination);
oscillator.frequency.value = 800;
oscillator.type = "square";
gainNode.gain.value = 0.2;
oscillator.start();
setTimeout(function(){oscillator.stop()},200);
}
playSound();
</script>
"""


# ───────── API FUNCTIONS ─────────
def fetch_history():
    try:
        r = requests.get(f"{API_BASE}/history?limit={HISTORY_LIMIT}", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        st.warning("⚠️ API connection failed")
    return []


def fetch_stats():
    try:
        r = requests.get(f"{API_BASE}/stats", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


def fetch_model():
    try:
        r = requests.get(f"{API_BASE}/model_info", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}


# ───────── BLOCK IP FUNCTION ─────────
def block_ip(ip):
    st.session_state.blocked_ips.add(ip)

    st.session_state.alert_log.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "action": f"🚫 Blocked IP {ip}"
    })


# ───────── SIDEBAR ─────────
with st.sidebar:

    st.title("🛡️ CyberThreat")

    auto_refresh = st.checkbox("Auto Refresh", True)

    st.session_state.sound_enabled = st.checkbox(
        "Sound Alerts",
        st.session_state.sound_enabled
    )

    st.markdown("---")

    st.subheader("Blocked IPs")

    for ip in list(st.session_state.blocked_ips):

        col1, col2 = st.columns([4, 1])

        with col1:
            st.write(ip)

        with col2:
            if st.button("❌", key=f"unblock_{ip}"):
                st.session_state.blocked_ips.remove(ip)
                st.rerun()


# ───────── HEADER ─────────
st.title("🛡️ Cyber Threat Detection Dashboard")
st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("---")


# ───────── FETCH DATA ─────────
history = fetch_history()
stats = fetch_stats()
model = fetch_model()


# ───────── SOUND ALERT ─────────
if history and st.session_state.sound_enabled:

    new_high = [
        h for h in history[-5:]
        if h.get("threat_level") == "HIGH"
        and h.get("timestamp") not in st.session_state.alerted_ids
    ]

    if new_high:

        components.html(ALERT_SOUND, height=0)

        for h in new_high:
            st.session_state.alerted_ids.add(h["timestamp"])


# ───────── KPI METRICS ─────────
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Requests", stats.get("total_requests", 0))
c2.metric("High Risk", stats.get("high_risk_count", 0))
c3.metric("Avg Risk Score", round(stats.get("avg_risk_score", 0), 2))
c4.metric("Blocked IPs", len(st.session_state.blocked_ips))

st.markdown("---")


# ───────── MODEL INFO ─────────
st.subheader("Model Performance")

m1, m2, m3 = st.columns(3)

m1.metric("Accuracy", f"{model.get('accuracy',0.97)*100:.1f}%")
m2.metric("Trees", model.get("n_estimators", 100))
m3.metric("Features", model.get("n_features", 78))


# ───────── ATTACK DISTRIBUTION ─────────
st.subheader("Attack Distribution")

attack_counts = stats.get("attack_counts", {})

if attack_counts:

    df = pd.DataFrame({
        "Attack": attack_counts.keys(),
        "Count": attack_counts.values()
    })

    fig = px.pie(
        df,
        values="Count",
        names="Attack",
        color="Attack",
        color_discrete_map=ATTACK_COLORS
    )

    st.plotly_chart(fig, use_container_width=True)


# ───────── GLOBAL THREAT MAP ─────────
st.subheader("🌍 Global Threat Map")

if history:

    df_map = pd.DataFrame(history)

    if "latitude" in df_map.columns and "longitude" in df_map.columns:
        st.map(df_map[["latitude", "longitude"]])
    else:
        st.info("Geo location data not available yet.")


# ───────── RISK GRAPH ─────────
st.subheader("Risk Score Over Time")

if history:

    df = pd.DataFrame(history[-50:])
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    fig = px.scatter(
        df,
        x="timestamp",
        y="risk_score",
        color="attack_type",
        color_discrete_map=ATTACK_COLORS
    )

    st.plotly_chart(fig, use_container_width=True)


# ───────── AI THREAT INTELLIGENCE ─────────
st.subheader("🧠 AI Threat Intelligence")

if history:

    df = pd.DataFrame(history)

    high = len(df[df["threat_level"] == "HIGH"])
    medium = len(df[df["threat_level"] == "MEDIUM"])
    low = len(df[df["threat_level"] == "LOW"])

    col1, col2, col3 = st.columns(3)

    col1.metric("🔴 High Risk Threats", high)
    col2.metric("🟡 Medium Risk Threats", medium)
    col3.metric("🟢 Low Risk Traffic", low)


# ───────── THREAT TIMELINE ─────────
st.subheader("📅 Threat Timeline")

if history:

    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    timeline = df.groupby(
        df["timestamp"].dt.floor("1min")
    ).size().reset_index(name="attacks")

    fig = px.line(
        timeline,
        x="timestamp",
        y="attacks",
        title="Attacks Per Minute"
    )

    st.plotly_chart(fig, use_container_width=True)


# ───────── LIVE ALERT PANEL ─────────
st.subheader("Live Threat Alerts")

if history:

    for idx, pred in enumerate(reversed(history[-10:])):

        attack = pred.get("attack_type")
        ip = pred.get("source_ip")
        risk = pred.get("risk_score", 0)
        level = pred.get("threat_level")

        if level == "HIGH":
            st.error(f"{attack} | {ip} | Risk {risk:.2f}")
        elif level == "MEDIUM":
            st.warning(f"{attack} | {ip} | Risk {risk:.2f}")
        else:
            st.info(f"{attack} | {ip} | Risk {risk:.2f}")

        if attack != "Other" and ip not in st.session_state.blocked_ips:

            if st.button(f"🚫 Block {ip}", key=f"block_{ip}_{idx}"):
                block_ip(ip)
                st.rerun()


# ───────── SUSPICIOUS IP TABLE ─────────
st.subheader("Suspicious IPs")

if history:

    df = pd.DataFrame(history)
    df = df[df["attack_type"] != "Other"]

    if not df.empty:

        table = (
            df.groupby("source_ip")
            .size()
            .reset_index(name="Attacks")
            .sort_values("Attacks", ascending=False)
        )

        st.dataframe(table.head(10), use_container_width=True)


# ───────── ACTION LOG ─────────
st.subheader("Action Log")

for log in reversed(st.session_state.alert_log[-10:]):
    st.write(log["time"], log["action"])


# ───────── AUTO REFRESH ─────────
if auto_refresh:
    time.sleep(REFRESH_SECS)
    st.rerun()