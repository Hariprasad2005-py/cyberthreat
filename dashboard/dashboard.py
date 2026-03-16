"""
dashboard.py — CyberThreat Detection Dashboard
Fixes:
1. Blocked IPs count updates correctly
2. Sound plays on HIGH threat (after Arm Sound click)
3. No duplicate button key errors
"""

import time
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_BASE      = "https://cyberthreat-api.onrender.com"
REFRESH_SECS  = 5
HISTORY_LIMIT = 100

ATTACK_COLORS = {
    "Other"  : "#ec4899",
    "DDoS"   : "#ef4444",
    "Botnet" : "#22c55e",
}

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyberThreat Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── SESSION STATE — all lists, no sets ───────────────────────────────────────
if "blocked_ips"   not in st.session_state: st.session_state.blocked_ips   = []
if "alerted_ids"   not in st.session_state: st.session_state.alerted_ids   = []
if "alert_log"     not in st.session_state: st.session_state.alert_log     = []
if "sound_armed"   not in st.session_state: st.session_state.sound_armed   = False
if "show_popup"    not in st.session_state: st.session_state.show_popup    = None

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
    [data-testid="stMetricLabel"] { color: #1e293b !important; font-weight: 600 !important; font-size: 0.9em !important; }
    [data-testid="stMetricValue"] { color: #0f172a !important; font-size: 2em !important; font-weight: 700 !important; }
    h1, h2, h3 { color: #f1f5f9; }
    .stSidebar { background-color: #1e293b; }
    section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: #334155 !important; color: #f1f5f9 !important;
        border: 1px solid #475569 !important; border-radius: 8px !important; font-weight: 600 !important;
    }
    .blocked-badge { background:#dc2626; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em; font-weight:bold; }
    .anomaly-badge { background:#7c3aed; color:white; padding:2px 8px; border-radius:4px; font-size:0.8em; font-weight:bold; }
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

def fetch_model_info():
    try:
        r = requests.get(f"{API_BASE}/model_info", timeout=3)
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

def block_ip(ip):
    if ip not in st.session_state.blocked_ips:
        st.session_state.blocked_ips.append(ip)
        st.session_state.alert_log.append({
            "time"  : datetime.now().strftime("%H:%M:%S"),
            "action": f"🚫 Blocked IP: {ip}",
            "type"  : "block"
        })

# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛡️ CyberThreat")
    st.markdown("**AI-Powered Network Monitor**")
    st.markdown("---")

    if api_online():
        st.success("🟢 API Online")
    else:
        st.error("🔴 API Offline")

    st.markdown("---")
    auto_refresh = st.checkbox("Auto Refresh (5s)", value=True)
    sound_enabled = st.checkbox("🔊 Sound Alerts", value=True)

    if sound_enabled:
        if not st.session_state.sound_armed:
            if st.button("🔔 Arm Sound (click once)"):
                st.session_state.sound_armed = True
                st.rerun()
            st.warning("⚠️ Click above to enable sound")
        else:
            st.success("🔊 Sound Armed!")
            if st.button("🔕 Disarm Sound"):
                st.session_state.sound_armed = False
                st.rerun()

    if st.button("🔄 Manual Refresh"):
        st.rerun()

    st.markdown("---")
    st.markdown("**Legend**")
    for attack, color in ATTACK_COLORS.items():
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:6px 0;">'
            f'<div style="width:20px;height:20px;background:{color};border-radius:4px;margin-right:10px;"></div>'
            f'<span style="color:#f1f5f9;">{attack}</span></div>',
            unsafe_allow_html=True
        )

    if st.session_state.blocked_ips:
        st.markdown("---")
        st.markdown("**🚫 Blocked IPs**")
        for bip in list(st.session_state.blocked_ips):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f'<span style="color:#ef4444;font-size:0.85em;">{bip}</span>', unsafe_allow_html=True)
            with c2:
                if st.button("✕", key=f"unblock_sidebar_{bip}"):
                    st.session_state.blocked_ips.remove(bip)
                    st.rerun()

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.title("🛡️ CyberThreat Detection Dashboard")
st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
st.markdown("---")

# ─── FETCH DATA ───────────────────────────────────────────────────────────────
history    = fetch_history()
stats      = fetch_stats()
model_info = fetch_model_info()

# ─── HIGH RISK DETECTION: SOUND + POPUP ───────────────────────────────────────
if history:
    new_high = [
        p for p in history[-5:]
        if p.get("threat_level") == "HIGH"
        and p.get("timestamp", "") not in st.session_state.alerted_ids
    ]
    if new_high:
        # Register all new alerts
        for p in new_high:
            ts = p.get("timestamp", "")
            if ts not in st.session_state.alerted_ids:
                st.session_state.alerted_ids.append(ts)
                st.session_state.alert_log.append({
                    "time"  : datetime.now().strftime("%H:%M:%S"),
                    "action": f"🔴 HIGH RISK: {p.get('attack_type')} from {p.get('source_ip')}",
                    "type"  : "alert"
                })
        st.session_state.show_popup = new_high[-1]

# Show popup if there's a pending alert
if st.session_state.show_popup:
    latest = st.session_state.show_popup
    attack = latest.get('attack_type', 'Unknown')
    src_ip = latest.get('source_ip', 'N/A')
    risk   = latest.get('risk_score', 0)

    # Sound JS — plays when armed
    if sound_enabled and st.session_state.sound_armed:
        st.markdown("""
        <script>
        (function() {
            try {
                var ctx = new (window.AudioContext || window.webkitAudioContext)();
                function beep(f, s, d) {
                    var o = ctx.createOscillator(), g = ctx.createGain();
                    o.connect(g); g.connect(ctx.destination);
                    o.frequency.value = f; o.type = 'sine';
                    g.gain.setValueAtTime(1, ctx.currentTime + s);
                    g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + s + d);
                    o.start(ctx.currentTime + s);
                    o.stop(ctx.currentTime + s + d + 0.05);
                }
                beep(880, 0.0, 0.2); beep(660, 0.3, 0.2); beep(880, 0.6, 0.3);
            } catch(e) {}
        })();
        </script>
        """, unsafe_allow_html=True)

    # Big popup
    st.markdown(f"""
    <div id="cyberPopup" style="
        position:fixed; top:0; left:0; width:100%; height:100%;
        background:rgba(0,0,0,0.82); z-index:999999;
        display:flex; align-items:center; justify-content:center;">
        <div style="
            background:linear-gradient(135deg,#1a0000,#3d0000);
            border:3px solid #ef4444; border-radius:20px;
            padding:50px 60px; text-align:center; max-width:600px;
            box-shadow:0 0 80px #ef4444,0 0 160px rgba(239,68,68,0.5);
            animation:pulse 1s infinite;">
            <div style="font-size:5em;">🚨</div>
            <div style="color:#ef4444;font-size:2.5em;font-weight:900;
                letter-spacing:3px;margin:10px 0;text-transform:uppercase;">
                ⚠ THREAT DETECTED ⚠
            </div>
            <div style="color:#fca5a5;font-size:1.4em;margin:8px 0;">
                Attack: <b style="color:#ef4444;">{attack}</b>
            </div>
            <div style="color:#fca5a5;font-size:1.2em;margin:8px 0;">
                Source IP: <b style="color:#fbbf24;">{src_ip}</b>
            </div>
            <div style="color:#fca5a5;font-size:1.2em;margin:8px 0 30px 0;">
                Risk Score: <b style="color:#ef4444;">{risk:.2f}</b> &nbsp;|&nbsp;
                Level: <b style="color:#ef4444;">HIGH</b>
            </div>
            <button onclick="document.getElementById('cyberPopup').remove()"
                style="background:#ef4444;color:white;border:none;border-radius:10px;
                    padding:14px 40px;font-size:1.1em;font-weight:700;cursor:pointer;">
                ✕ DISMISS
            </button>
        </div>
    </div>
    <style>
    @keyframes pulse {{
        0%   {{ box-shadow:0 0 80px #ef4444,0 0 160px rgba(239,68,68,0.5); }}
        50%  {{ box-shadow:0 0 120px #ef4444,0 0 240px rgba(239,68,68,0.8); }}
        100% {{ box-shadow:0 0 80px #ef4444,0 0 160px rgba(239,68,68,0.5); }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # Clear popup after showing
    st.session_state.show_popup = None

# ─── KPI METRICS ──────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric("📦 Total Requests",  stats.get("total_requests", 0))
with c2: st.metric("📊 Avg Risk Score",  f"{stats.get('avg_risk_score', 0):.2f}")
with c3: st.metric("⚠️ High Risk Events", stats.get("high_risk_count", 0))
with c4:
    ac = dict(stats.get("attack_counts", {}))
    ac.pop("Normal Traffic", None)
    st.metric("🚨 Attack Types", len(ac))
with c5: st.metric("🚫 Blocked IPs", len(st.session_state.blocked_ips))

st.markdown("---")

# ─── MODEL PERFORMANCE ────────────────────────────────────────────────────────
st.subheader("🤖 Model Performance")
acc       = model_info.get("accuracy", 0.97)
anomaly_p = model_info.get("anomaly_contamination", 0.05)
n_feat    = model_info.get("n_features", 78)
n_trees   = model_info.get("n_estimators", 100)

m1, m2, m3, m4 = st.columns(4)
with m1: st.metric("🎯 Model Accuracy",    f"{acc*100:.1f}%")
with m2: st.metric("🌲 Decision Trees",    n_trees)
with m3: st.metric("📐 Features Used",     n_feat)
with m4: st.metric("🔍 Anomaly Threshold", f"{anomaly_p*100:.0f}%")

st.markdown("---")

# ─── CHARTS ───────────────────────────────────────────────────────────────────
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("📊 Attack Distribution")
    all_counts = stats.get("attack_counts", {})
    if all_counts:
        df_pie = pd.DataFrame({"Attack Type": list(all_counts.keys()), "Count": list(all_counts.values())})
        fig_pie = px.pie(df_pie, values="Count", names="Attack Type",
                         color="Attack Type", color_discrete_map=ATTACK_COLORS, hole=0.4)
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font_color="#000000", legend=dict(font=dict(color="#000000")))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No data yet.")

with right_col:
    st.subheader("📈 Risk Score Over Time")
    if history:
        df_hist = pd.DataFrame(history[-50:])
        df_hist["timestamp"] = pd.to_datetime(df_hist["timestamp"])
        fig_line = px.scatter(df_hist, x="timestamp", y="risk_score",
                              color="attack_type", color_discrete_map=ATTACK_COLORS, size_max=8)
        fig_line.add_hline(y=0.7, line_dash="dash", line_color="#ef4444", annotation_text="HIGH threshold")
        fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font_color="#000000", legend=dict(font=dict(color="#000000")),
                                yaxis=dict(range=[0, 1]))
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("No data yet.")

st.markdown("---")

# ─── LIVE THREAT ALERTS + ACTION LOG ──────────────────────────────────────────
st.subheader("🔔 Alerts Panel")
alerts_col, log_col = st.columns([2, 1])

with alerts_col:
    st.subheader("⚠️ Live Threat Alerts")
    if history:
        threats = [p for p in reversed(history) if p.get("attack_type") != "Other"]
        normals = [p for p in reversed(history) if p.get("attack_type") == "Other"]
        display = (threats + normals)[:10]

        # Deduplicate IPs for buttons — only show block button for first occurrence of each IP
        seen_ips = set()

        for idx, pred in enumerate(display):
            attack     = pred.get("attack_type", "Unknown")
            risk       = pred.get("risk_score", 0)
            ip         = pred.get("source_ip", "N/A")
            level      = pred.get("threat_level", "LOW")
            ts         = pred.get("timestamp", "")[:19].replace("T", " ")
            badge      = threat_level_badge(level)
            border     = ATTACK_COLORS.get(attack, "#6b7280")
            is_blocked = ip in st.session_state.blocked_ips
            is_anomaly = pred.get("is_anomaly", False)

            blocked_tag = '<span class="blocked-badge">BLOCKED</span>' if is_blocked else ""
            anomaly_tag = '<span class="anomaly-badge">ANOMALY</span>' if is_anomaly else ""

            st.markdown(f"""
            <div style="background:#1e293b;border-left:4px solid {border};
                        border-radius:8px;padding:14px;margin:6px 0;">
                <b style="color:#f1f5f9;font-size:1.05em;">
                    {badge} {'Threat Detected ⚠️' if attack != 'Other' else '✅ Normal Traffic'}
                </b> {blocked_tag} {anomaly_tag}<br>
                <span style="color:#94a3b8;">Attack: </span>
                <span style="color:{border};font-weight:bold;">{attack}</span> &nbsp;|&nbsp;
                <span style="color:#94a3b8;">Risk: </span>
                <span style="color:#f97316;font-weight:bold;">{level}</span><br>
                <span style="color:#94a3b8;">IP: </span>
                <span style="color:#e2e8f0;">{ip}</span> &nbsp;|&nbsp;
                <span style="color:#94a3b8;">Score: </span>
                <span style="color:#f1f5f9;">{risk:.2f}</span> &nbsp;|&nbsp;
                <span style="color:#64748b;">{ts}</span>
            </div>
            """, unsafe_allow_html=True)

            # Only show block button for first occurrence of each IP
            if attack != "Other" and not is_blocked and ip not in seen_ips:
                seen_ips.add(ip)
                if st.button(f"🚫 Block {ip}", key=f"blockbtn_{idx}_{ip}"):
                    block_ip(ip)
                    st.rerun()
    else:
        st.info("No predictions yet.")

with log_col:
    st.subheader("📋 Action Log")
    if st.session_state.alert_log:
        for entry in reversed(st.session_state.alert_log[-15:]):
            color = "#ef4444" if entry["type"] == "alert" else "#f97316"
            st.markdown(
                f'<div style="background:#1e293b;border-radius:6px;padding:8px;margin:4px 0;">'
                f'<span style="color:#64748b;font-size:0.8em;">{entry["time"]}</span><br>'
                f'<span style="color:{color};font-size:0.85em;">{entry["action"]}</span></div>',
                unsafe_allow_html=True
            )
        if st.button("🗑️ Clear Log"):
            st.session_state.alert_log = []
            st.rerun()
    else:
        st.info("No actions yet.")

st.markdown("---")

# ─── ANOMALY DETECTION ────────────────────────────────────────────────────────
st.subheader("🔍 Anomaly Detection (Isolation Forest)")

if history:
    df_all    = pd.DataFrame(history)
    total     = len(df_all)
    n_anomaly = int(df_all["is_anomaly"].sum()) if "is_anomaly" in df_all.columns else int(total * 0.05)
    n_normal  = total - n_anomaly

    a1, a2, a3 = st.columns(3)
    with a1: st.metric("🔍 Anomalies Detected", n_anomaly)
    with a2: st.metric("✅ Normal Traffic",      n_normal)
    with a3: st.metric("📊 Anomaly Rate",        f"{round(n_anomaly/total*100,1) if total else 0}%")

    df_chart = pd.DataFrame({"Category": ["Normal", "Anomaly"], "Count": [n_normal, n_anomaly]})
    fig_anom = px.bar(df_chart, x="Category", y="Count", color="Category",
                      color_discrete_map={"Normal": "#22c55e", "Anomaly": "#ef4444"},
                      title="Normal vs Anomalous Traffic")
    fig_anom.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font_color="#000000", showlegend=False)
    st.plotly_chart(fig_anom, use_container_width=True)
else:
    st.info("Waiting for data...")

st.markdown("---")

# ─── SUSPICIOUS IPs TABLE ─────────────────────────────────────────────────────
st.subheader("🌐 Suspicious IP Addresses")

if history:
    df_all = pd.DataFrame(history)
    df_sus = df_all[df_all["attack_type"] != "Other"].copy()

    if not df_sus.empty:
        ip_summary = (
            df_sus.groupby("source_ip")
            .agg(attack_count=("attack_type","count"), last_attack=("attack_type","last"),
                 avg_risk=("risk_score","mean"), last_seen=("timestamp","last"))
            .sort_values("attack_count", ascending=False)
            .reset_index().head(15)
        )
        ip_summary["avg_risk"]  = ip_summary["avg_risk"].round(3)
        ip_summary["last_seen"] = ip_summary["last_seen"].str[:19].str.replace("T", " ")
        ip_summary["status"]    = ip_summary["source_ip"].apply(
            lambda x: "🚫 Blocked" if x in st.session_state.blocked_ips else "🟢 Active"
        )
        st.dataframe(ip_summary.rename(columns={
            "source_ip":"Source IP","attack_count":"# Attacks",
            "last_attack":"Last Attack","avg_risk":"Avg Risk",
            "last_seen":"Last Seen","status":"Status"
        }), use_container_width=True)

        # Quick block buttons — unique keys using enumerate
        st.markdown("**Quick Block:**")
        top5 = ip_summary[ip_summary["source_ip"].apply(lambda x: x not in st.session_state.blocked_ips)].head(5)
        cols = st.columns(min(5, len(top5)) or 1)
        for i, (_, row) in enumerate(top5.iterrows()):
            qip = row["source_ip"]
            with cols[i % 5]:
                if st.button(f"🚫 {qip}", key=f"quickblock_{i}_{qip}"):
                    block_ip(qip)
                    st.rerun()
    else:
        st.success("✅ No suspicious IPs detected.")
else:
    st.info("Waiting for data…")

# ─── AUTO REFRESH ─────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(REFRESH_SECS)
    st.rerun()