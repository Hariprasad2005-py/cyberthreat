"""
dashboard.py
------------
Step 5: Streamlit Cybersecurity Monitoring Dashboard
"""

import time
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_BASE      = "http://127.0.0.1:5000"
REFRESH_SECS  = 5
HISTORY_LIMIT = 100

ATTACK_COLORS = {
    "Other"  : "#ec4899",   # pink
    "DDoS"   : "#ef4444",   # red
    "Botnet" : "#22c55e",   # green
}

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyberThreat Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f172a; }

    [data-testid="stMetric"] {
        background: #f1f5f9 !important;
        border-radius: 12px !important;
        padding: 16px !important;
        border: 1px solid #cbd5e1;
    }
    [data-testid="stMetricLabel"] {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-size: 0.9em !important;
    }
    [data-testid="stMetricValue"] {
        color: #0f172a !important;
        font-size: 2em !important;
        font-weight: 700 !important;
    }

    .threat-card {
        background: #1e293b; border-left: 4px solid #ef4444;
        border-radius: 8px; padding: 16px; margin: 8px 0;
    }
    .safe-card {
        background: #1e293b; border-left: 4px solid #ec4899;
        border-radius: 8px; padding: 16px; margin: 8px 0;
    }
    h1, h2, h3 { color: #f1f5f9; }
    .stSidebar { background-color: #1e293b; }

    section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] .stCheckbox label {
        color: #f1f5f9 !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stButton button {
        background: #334155 !important;
        color: #f1f5f9 !important;
        border: 1px solid #475569 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #475569 !important;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div { color: #f1f5f9 !important; }
</style>
""", unsafe_allow_html=True)

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def fetch_history(limit=HISTORY_LIMIT):
    try:
        r = requests.get(f"{API_BASE}/history?limit={limit}", timeout=3)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []

def fetch_stats():
    try:
        r = requests.get(f"{API_BASE}/stats", timeout=3)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

def api_online():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def threat_level_badge(level):
    return {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(level, "⚪")

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛡️ CyberThreat")
    st.markdown("**AI-Powered Network Monitor**")
    st.markdown("---")

    if api_online():
        st.success("🟢 API Online")
    else:
        st.error("🔴 API Offline — start backend/app.py")

    st.markdown("---")
    auto_refresh = st.checkbox("Auto Refresh (5s)", value=True)
    if st.button("🔄 Manual Refresh"):
        st.rerun()

    st.markdown("---")
    st.markdown("**Legend**")
    for attack, color in ATTACK_COLORS.items():
        st.markdown(
            f'<div style="display:flex; align-items:center; margin:6px 0;">'
            f'<div style="width:20px; height:20px; background:{color}; border-radius:4px; margin-right:10px;"></div>'
            f'<span style="color:#f1f5f9; font-size:1em;">{attack}</span>'
            f'</div>',
            unsafe_allow_html=True
        )

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.title("🛡️ CyberThreat Detection Dashboard")
st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
st.markdown("---")

# ─── FETCH DATA ───────────────────────────────────────────────────────────────
history = fetch_history()
stats   = fetch_stats()

# ─── KPI METRICS ──────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("📦 Total Requests", stats.get("total_requests", 0))
with col2:
    avg_risk = stats.get("avg_risk_score", 0)
    st.metric("📊 Avg Risk Score", f"{avg_risk:.2f}")
with col3:
    st.metric("⚠️ High Risk Events", stats.get("high_risk_count", 0))
with col4:
    attack_counts = stats.get("attack_counts", {})
    attack_counts.pop("Normal Traffic", None)
    st.metric("🚨 Attack Types", len(attack_counts))

st.markdown("---")

# ─── CHARTS ROW ───────────────────────────────────────────────────────────────
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("📊 Attack Distribution")
    all_counts = stats.get("attack_counts", {})
    if all_counts:
        df_pie = pd.DataFrame({
            "Attack Type": list(all_counts.keys()),
            "Count"      : list(all_counts.values()),
        })
        fig_pie = px.pie(
            df_pie, values="Count", names="Attack Type",
            color="Attack Type",
            color_discrete_map=ATTACK_COLORS,
            hole=0.4,
        )
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#000000",
            legend=dict(font=dict(color="#000000")),
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No data yet. Start the simulator.")

with right_col:
    st.subheader("📈 Risk Score Over Time")
    if history:
        df_hist = pd.DataFrame(history[-50:])
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
        fig_line = px.scatter(
            df_hist, x="timestamp", y="risk_score",
            color="attack_type",
            color_discrete_map=ATTACK_COLORS,
            size_max=8,
        )
        fig_line.add_hline(
            y=0.7, line_dash="dash",
            line_color="#ef4444", annotation_text="HIGH threshold"
        )
        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#000000",
            legend=dict(font=dict(color="#000000")),
            yaxis=dict(range=[0, 1]),
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No data yet.")

st.markdown("---")

# ─── THREAT ALERTS ────────────────────────────────────────────────────────────
st.subheader("⚠️ Live Threat Alerts")

if history:
    threats = [p for p in reversed(history) if p.get("attack_type") != "Other"]
    normals = [p for p in reversed(history) if p.get("attack_type") == "Other"]
    display = (threats + normals)[:10]

    for pred in display:
        attack = pred.get("attack_type", "Unknown")
        risk   = pred.get("risk_score", 0)
        ip     = pred.get("source_ip", "N/A")
        level  = pred.get("threat_level", "LOW")
        ts     = pred.get("timestamp", "")[:19].replace("T", " ")
        badge  = threat_level_badge(level)
        border = ATTACK_COLORS.get(attack, "#6b7280")

        st.markdown(f"""
        <div style="background:#1e293b; border-left:4px solid {border};
                    border-radius:8px; padding:14px; margin:6px 0;">
            <b style="color:#f1f5f9; font-size:1.05em;">
                {badge} {'Threat Detected ⚠️' if attack != 'Other' else '✅ Normal / Other Traffic'}
            </b><br>
            <span style="color:#94a3b8;">Attack Type: </span>
            <span style="color:{border}; font-weight:bold;">{attack}</span> &nbsp;|&nbsp;
            <span style="color:#94a3b8;">Risk Level: </span>
            <span style="color:#f97316; font-weight:bold;">{level}</span><br>
            <span style="color:#94a3b8;">Source IP: </span>
            <span style="color:#e2e8f0;">{ip}</span> &nbsp;|&nbsp;
            <span style="color:#94a3b8;">Risk Score: </span>
            <span style="color:#f1f5f9;">{risk:.2f}</span> &nbsp;|&nbsp;
            <span style="color:#64748b;">{ts}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No predictions yet. Start the simulator or send traffic to the API.")

st.markdown("---")

# ─── SUSPICIOUS IPs TABLE ─────────────────────────────────────────────────────
st.subheader("🌐 Suspicious IP Addresses")

if history:
    df_all = pd.DataFrame(history)
    df_sus = df_all[df_all["attack_type"] != "Other"].copy()

    if not df_sus.empty:
        ip_summary = (
            df_sus.groupby("source_ip")
            .agg(
                attack_count=("attack_type", "count"),
                last_attack=("attack_type", "last"),
                avg_risk=("risk_score", "mean"),
                last_seen=("timestamp", "last"),
            )
            .sort_values("attack_count", ascending=False)
            .reset_index()
            .head(15)
        )
        ip_summary["avg_risk"]  = ip_summary["avg_risk"].round(3)
        ip_summary["last_seen"] = ip_summary["last_seen"].str[:19].str.replace("T", " ")
        st.dataframe(
            ip_summary.rename(columns={
                "source_ip"   : "Source IP",
                "attack_count": "# Attacks",
                "last_attack" : "Last Attack Type",
                "avg_risk"    : "Avg Risk",
                "last_seen"   : "Last Seen",
            }),
            use_container_width=True,
        )
    else:
        st.success("✅ No suspicious IPs detected.")
else:
    st.info("Waiting for data …")

# ─── AUTO REFRESH ─────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(REFRESH_SECS)
    st.rerun()