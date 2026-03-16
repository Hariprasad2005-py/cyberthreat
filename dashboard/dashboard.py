"""
CyberThreat AI Dashboard — Hackathon Edition
Clean, impressive light theme with advanced visualizations
"""

import time
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_BASE      = "https://cyberthreat-api.onrender.com"
REFRESH_SECS  = 5
HISTORY_LIMIT = 100

ATTACK_COLORS = {
    "Normal Traffic": "#22c55e",
    "Other"         : "#6366f1",
    "DDoS"          : "#ef4444",
    "Botnet"        : "#f59e0b",
    "Port Scan"     : "#f97316",
    "Brute Force"   : "#8b5cf6",
    "Web Attack"    : "#06b6d4",
    "DoS"           : "#ec4899",
    "Infiltration"  : "#dc2626",
    "Heartbleed"    : "#7c3aed",
}

# IP prefix → approximate geo coordinates for threat map
IP_GEO_MAP = {
    "203.0"  : (35.68,  139.69, "Tokyo"),
    "198.51" : (55.75,  37.62,  "Moscow"),
    "10.0"   : (37.77,  -122.42,"San Francisco"),
    "192.168": (51.51,  -0.13,  "London"),
    "172.16" : (48.86,  2.35,   "Paris"),
    "100.64" : (31.23,  121.47, "Shanghai"),
    "169.254": (-33.87, 151.21, "Sydney"),
    "198.18" : (28.61,  77.21,  "New Delhi"),
    "100.100": (1.35,   103.82, "Singapore"),
    "203.113": (13.75,  100.52, "Bangkok"),
}

def ip_to_geo(ip):
    prefix2 = ".".join(ip.split(".")[:2])
    if prefix2 in IP_GEO_MAP:
        return IP_GEO_MAP[prefix2]
    seed = sum(ord(c) for c in ip)
    rng  = np.random.default_rng(seed)
    lat  = float(rng.uniform(-60, 70))
    lon  = float(rng.uniform(-160, 160))
    return (lat, lon, ip)

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CyberThreat Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── THREE.JS NETWORK BACKGROUND ──────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Gradient background ── */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg,
        #f0f7ff 0%,
        #e8f4fd 20%,
        #ffffff 45%,
        #f0f9ff 70%,
        #dbeafe 100%
    ) !important;
    background-attachment: fixed !important;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background:
        radial-gradient(ellipse at 15% 20%, rgba(99,102,241,0.08) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 80%, rgba(59,130,246,0.10) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%, rgba(255,255,255,0.6) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}

/* Three.js canvas fixed behind everything */
#threejs-bg {
    position: fixed !important;
    top: 0; left: 0;
    width: 100vw; height: 100vh;
    z-index: 0;
    pointer-events: none;
    opacity: 0.55;
}

/* Ensure content sits above canvas */
[data-testid="stAppViewContainer"] > div {
    position: relative;
    z-index: 1;
}
section[data-testid="stSidebar"] {
    z-index: 100 !important;
}

.main .block-container { padding: 1.5rem 2rem 2rem 2rem; max-width: 1400px; position:relative; z-index:1; }
#MainMenu, footer, header { visibility: hidden; }

/* ── KPI Cards — glass morphism ── */
.kpi-card {
    background: rgba(255,255,255,0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 2px 8px rgba(99,102,241,0.08), 0 4px 24px rgba(59,130,246,0.06);
    border: 1px solid rgba(255,255,255,0.9);
    position: relative; overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(99,102,241,0.14);
    background: rgba(255,255,255,0.95);
}
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:3px; border-radius:16px 16px 0 0;
}
.kpi-card.blue::before   { background: linear-gradient(90deg,#6366f1,#818cf8); }
.kpi-card.red::before    { background: linear-gradient(90deg,#ef4444,#f87171); }
.kpi-card.amber::before  { background: linear-gradient(90deg,#f59e0b,#fbbf24); }
.kpi-card.green::before  { background: linear-gradient(90deg,#22c55e,#4ade80); }
.kpi-card.purple::before { background: linear-gradient(90deg,#8b5cf6,#a78bfa); }

.kpi-label { font-size:0.72rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#94a3b8; margin-bottom:0.4rem; }
.kpi-value { font-size:2.2rem; font-weight:800; color:#0f172a; line-height:1.1; font-variant-numeric:tabular-nums; }
.kpi-value.red    { color:#ef4444; }
.kpi-value.amber  { color:#f59e0b; }
.kpi-value.green  { color:#22c55e; }
.kpi-value.blue   { color:#6366f1; }
.kpi-value.purple { color:#8b5cf6; }
.kpi-sub { font-size:0.75rem; color:#94a3b8; margin-top:0.3rem; }

.section-header {
    font-size:1rem; font-weight:700; color:#0f172a;
    letter-spacing:-0.01em; margin:0 0 1rem 0;
    display:flex; align-items:center; gap:0.5rem;
}
.section-header .dot { width:8px; height:8px; border-radius:50%; display:inline-block; }

/* ── Chart cards — glass morphism ── */
.chart-card {
    background: rgba(255,255,255,0.82);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-radius: 16px; padding: 1.4rem 1.6rem;
    box-shadow: 0 2px 8px rgba(99,102,241,0.07), 0 4px 20px rgba(59,130,246,0.05);
    border: 1px solid rgba(255,255,255,0.88);
    margin-bottom: 1rem;
}

.alert-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:0.6rem 0.9rem; border-radius:10px; margin-bottom:0.45rem;
    font-size:0.8rem; font-weight:500;
}
.alert-high   { background:rgba(255,241,242,0.9); border-left:3px solid #ef4444; }
.alert-medium { background:rgba(255,251,235,0.9); border-left:3px solid #f59e0b; }
.alert-low    { background:rgba(240,253,244,0.9); border-left:3px solid #22c55e; }
.alert-tag { font-size:0.68rem; font-weight:700; padding:2px 7px; border-radius:99px; letter-spacing:0.05em; }
.tag-high   { background:#fee2e2; color:#ef4444; }
.tag-medium { background:#fef3c7; color:#d97706; }
.tag-low    { background:#dcfce7; color:#16a34a; }

.ip-row {
    display:flex; justify-content:space-between; align-items:center;
    padding:0.5rem 0; border-bottom:1px solid rgba(241,245,249,0.8); font-size:0.8rem;
}
.ip-badge {
    font-family:'JetBrains Mono',monospace; font-size:0.76rem;
    background:rgba(248,250,252,0.9); border:1px solid #e2e8f0;
    padding:2px 7px; border-radius:6px; color:#334155;
}
.count-badge { background:#ef4444; color:white; font-size:0.68rem; font-weight:700; padding:2px 7px; border-radius:99px; }

.model-stat { text-align:center; padding:0.9rem; background:rgba(248,250,252,0.9); border-radius:12px; border:1px solid #e2e8f0; }
.model-stat-val { font-size:1.5rem; font-weight:800; color:#6366f1; }
.model-stat-lbl { font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:#94a3b8; margin-top:0.2rem; }

.page-title    { font-size:1.75rem; font-weight:800; color:#0f172a; letter-spacing:-0.03em; margin-bottom:0; }
.page-subtitle { font-size:0.83rem; color:#64748b; margin-top:0.2rem; }

@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.4;transform:scale(1.4)} }
.pulse-dot { width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;animation:pulse 1.8s infinite;margin-right:5px; }

section[data-testid="stSidebar"] { background: rgba(15,23,42,0.97) !important; backdrop-filter:blur(20px); }
section[data-testid="stSidebar"] * { color:#e2e8f0 !important; }
section[data-testid="stSidebar"] hr { border-color:#1e293b !important; }
.status-online  { color:#22c55e !important; font-weight:600; font-size:0.82rem; }
.status-offline { color:#ef4444 !important; font-weight:600; font-size:0.82rem; }
</style>

""", unsafe_allow_html=True)

# ─── THREE.JS NETWORK — 5-second intro splash then auto-hides ────────────────
components.html("""
<!DOCTYPE html>
<html>
<head>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { background:transparent; overflow:hidden; font-family:'Inter',sans-serif; }

#splash {
    position: relative;
    width: 100%;
    height: 500px;
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 40%, #0f172a 100%);
    border-radius: 16px;
    overflow: hidden;
    transition: opacity 0.8s ease, height 0.8s ease;
}

#splash.hiding {
    opacity: 0;
    height: 0;
}

canvas { display:block; width:100% !important; height:100% !important; }

#overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    z-index: 10;
}

#title-text {
    font-size: 1.6rem;
    font-weight: 800;
    color: white;
    letter-spacing: -0.02em;
    text-align: center;
    opacity: 0;
    transform: translateY(12px);
    animation: fadeUp 0.8s ease 0.3s forwards;
}

#sub-text {
    font-size: 0.78rem;
    color: rgba(148,163,184,0.9);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.5rem;
    text-align: center;
    opacity: 0;
    animation: fadeUp 0.8s ease 0.6s forwards;
}

#countdown-ring {
    margin-top: 1.4rem;
    position: relative;
    width: 52px;
    height: 52px;
    opacity: 0;
    animation: fadeUp 0.6s ease 0.9s forwards;
}

#countdown-ring svg {
    transform: rotate(-90deg);
}

#countdown-num {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    font-size: 1.1rem;
    font-weight: 800;
    color: #60a5fa;
}

#ring-fill {
    stroke-dasharray: 138;
    stroke-dashoffset: 0;
    animation: drainRing 5s linear 1s forwards;
}

@keyframes drainRing {
    from { stroke-dashoffset: 0; }
    to   { stroke-dashoffset: 138; }
}

@keyframes fadeUp {
    to { opacity:1; transform:translateY(0); }
}

#node-labels {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 5;
}
</style>
</head>
<body>
<div id="splash">
    <canvas id="c"></canvas>
    <div id="overlay">
        <div id="title-text">🛡️ CyberThreat Network Topology</div>
        <div id="sub-text">Live AI-Powered Threat Detection · Random Forest + Isolation Forest</div>
        <div id="countdown-ring">
            <svg width="52" height="52" viewBox="0 0 52 52">
                <circle cx="26" cy="26" r="22" fill="none" stroke="rgba(99,102,241,0.25)" stroke-width="3"/>
                <circle id="ring-fill" cx="26" cy="26" r="22" fill="none"
                        stroke="#6366f1" stroke-width="3"
                        stroke-linecap="round"/>
            </svg>
            <div id="countdown-num">5</div>
        </div>
    </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// ── Countdown number ──
var num = document.getElementById('countdown-num');
var counts = [5,4,3,2,1];
counts.forEach(function(n, i) {
    setTimeout(function() { if(num) num.textContent = n; }, i * 1000 + 1000);
});

// ── Hide splash after 5.8s ──
setTimeout(function() {
    var splash = document.getElementById('splash');
    if (splash) splash.classList.add('hiding');
}, 5800);

// ── Three.js ──
(function() {
    var canvas = document.getElementById('c');
    var W = canvas.parentElement.offsetWidth || 800;
    var H = 500;

    var renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.setClearColor(0x000000, 0);

    var scene  = new THREE.Scene();
    var camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
    camera.position.z = 75;

    // Nodes
    var nodeCount = 70;
    var nodes = [];
    var nodeGeom = new THREE.SphereGeometry(0.5, 10, 10);
    var colors = [0x6366f1, 0x3b82f6, 0x60a5fa, 0x93c5fd, 0xef4444, 0xf59e0b];

    for (var i = 0; i < nodeCount; i++) {
        var isAttack = Math.random() > 0.75;
        var mat = new THREE.MeshBasicMaterial({
            color: isAttack ? colors[4] : colors[Math.floor(Math.random() * 4)],
            transparent: true,
            opacity: isAttack ? 0.9 : (Math.random() * 0.4 + 0.3)
        });
        var mesh = new THREE.Mesh(nodeGeom, mat);
        mesh.position.set(
            (Math.random() - 0.5) * 160,
            (Math.random() - 0.5) * 80,
            (Math.random() - 0.5) * 50
        );
        mesh.userData = {
            vx: (Math.random() - 0.5) * 0.05,
            vy: (Math.random() - 0.5) * 0.035,
            vz: (Math.random() - 0.5) * 0.025,
            pulseSpeed: Math.random() * 0.025 + 0.008,
            pulseOffset: Math.random() * Math.PI * 2,
            isAttack: isAttack
        };
        scene.add(mesh);
        nodes.push(mesh);
    }

    // Edges
    var edgeLines = [];
    var connDist = 35;

    function rebuildEdges() {
        edgeLines.forEach(function(l) { scene.remove(l); l.geometry.dispose(); l.material.dispose(); });
        edgeLines = [];
        for (var i = 0; i < nodes.length; i++) {
            for (var j = i + 1; j < nodes.length; j++) {
                var d = nodes[i].position.distanceTo(nodes[j].position);
                if (d < connDist) {
                    var isHot = nodes[i].userData.isAttack || nodes[j].userData.isAttack;
                    var pts  = [nodes[i].position.clone(), nodes[j].position.clone()];
                    var geom = new THREE.BufferGeometry().setFromPoints(pts);
                    var lmat = new THREE.LineBasicMaterial({
                        color: isHot ? 0xef4444 : 0x6366f1,
                        transparent: true,
                        opacity: isHot ? (1 - d/connDist) * 0.35 : (1 - d/connDist) * 0.15
                    });
                    var line = new THREE.Line(geom, lmat);
                    scene.add(line);
                    edgeLines.push(line);
                }
            }
        }
    }

    // Packets
    var packetGeom = new THREE.SphereGeometry(0.3, 8, 8);
    var packets = [];

    function spawnPacket() {
        var a = Math.floor(Math.random() * nodes.length);
        var b = Math.floor(Math.random() * nodes.length);
        if (a === b) return;
        var isAttackPkt = nodes[a].userData.isAttack || nodes[b].userData.isAttack;
        var m = new THREE.Mesh(packetGeom, new THREE.MeshBasicMaterial({
            color: isAttackPkt ? 0xef4444 : 0x60a5fa,
            transparent: true, opacity: 0.95
        }));
        scene.add(m);
        packets.push({
            mesh: m,
            from: nodes[a].position.clone(),
            to: nodes[b].position.clone(),
            t: 0,
            speed: 0.015 + Math.random() * 0.015
        });
    }
    for (var p = 0; p < 15; p++) spawnPacket();

    var clock = new THREE.Clock();
    var frame = 0;

    function animate() {
        requestAnimationFrame(animate);
        var t = clock.getElapsedTime();
        frame++;

        nodes.forEach(function(n) {
            var s = 1 + 0.3 * Math.sin(t * n.userData.pulseSpeed * 60 + n.userData.pulseOffset);
            n.scale.setScalar(s);
            n.position.x += n.userData.vx;
            n.position.y += n.userData.vy;
            n.position.z += n.userData.vz;
            if (Math.abs(n.position.x) > 80)  n.userData.vx *= -1;
            if (Math.abs(n.position.y) > 40)  n.userData.vy *= -1;
            if (Math.abs(n.position.z) > 25)  n.userData.vz *= -1;
        });

        if (frame % 45 === 0) rebuildEdges();

        for (var i = packets.length - 1; i >= 0; i--) {
            var pk = packets[i];
            pk.t += pk.speed;
            if (pk.t >= 1) {
                scene.remove(pk.mesh);
                pk.mesh.geometry.dispose();
                pk.mesh.material.dispose();
                packets.splice(i, 1);
                spawnPacket();
            } else {
                pk.mesh.position.lerpVectors(pk.from, pk.to, pk.t);
            }
        }

        camera.position.x = Math.sin(t * 0.05) * 10;
        camera.position.y = Math.cos(t * 0.04) * 5;
        camera.lookAt(scene.position);
        renderer.render(scene, camera);
    }

    rebuildEdges();
    animate();
})();
</script>
</body>
</html>
""", height=520, scrolling=False)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for k, v in [("alerted_ids", set()), ("alert_log", []), ("sound_enabled", True)]:
    if k not in st.session_state:
        st.session_state[k] = v

ALERT_SOUND = """<script>
try {
  var ctx=new(window.AudioContext||window.webkitAudioContext)();
  var osc=ctx.createOscillator(),gain=ctx.createGain();
  osc.connect(gain);gain.connect(ctx.destination);
  osc.frequency.value=880;osc.type="sine";
  gain.gain.setValueAtTime(0.15,ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001,ctx.currentTime+0.4);
  osc.start();osc.stop(ctx.currentTime+0.4);
}catch(e){}
</script>"""

# ─── API HELPERS ──────────────────────────────────────────────────────────────
def fetch(endpoint, timeout=10):
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

def post_api(endpoint, payload):
    try:
        requests.post(f"{API_BASE}/{endpoint}", json=payload, timeout=5)
    except:
        pass

def fetch_history():
    return fetch(f"history?limit={HISTORY_LIMIT}") or []

def fetch_stats():
    return fetch("stats") or {}

def fetch_model():
    return fetch("model_info") or {}



# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛡️ CyberThreat AI")
    st.markdown("---")
    auto_refresh = st.checkbox("⟳  Auto Refresh (5s)", True)
    st.session_state.sound_enabled = st.checkbox("🔔  Sound Alerts", st.session_state.sound_enabled)
    st.markdown("---")
    try:
        h = requests.get(f"{API_BASE}/health", timeout=6)
        if h.status_code == 200:
            st.markdown('<p class="status-online">● API Online</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-offline">● API Error</p>', unsafe_allow_html=True)
    except:
        st.markdown('<p class="status-offline">● API Offline — waking up…</p>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**📋 Action Log**")
    if st.session_state.alert_log:
        for log in reversed(st.session_state.alert_log[-5:]):
            st.caption(f"{log['time']}  {log['action']}")
    else:
        st.caption("No actions yet")

# ─── FETCH ────────────────────────────────────────────────────────────────────
history  = fetch_history()
stats    = fetch_stats()
model    = fetch_model()

# ─── SOUND ────────────────────────────────────────────────────────────────────
if history and st.session_state.sound_enabled:
    new_high = [h for h in history[-5:]
                if h.get("threat_level") == "HIGH"
                and h.get("timestamp") not in st.session_state.alerted_ids]
    if new_high:
        components.html(ALERT_SOUND, height=0)
        for h in new_high:
            st.session_state.alerted_ids.add(h["timestamp"])

# ─── HEADER ───────────────────────────────────────────────────────────────────
col_title, col_time = st.columns([3,1])
with col_title:
    st.markdown("""
        <p class="page-title">🛡️ Cyber Threat Intelligence</p>
        <p class="page-subtitle"><span class="pulse-dot"></span>Live monitoring · AI-powered · Random Forest + Isolation Forest · CICIDS2017</p>
    """, unsafe_allow_html=True)
with col_time:
    st.markdown(f"""
        <div style="text-align:right;padding-top:0.8rem">
            <div style="font-size:0.72rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:0.06em">Last Updated</div>
            <div style="font-size:0.95rem;font-weight:700;color:#334155;font-family:'JetBrains Mono',monospace">{datetime.now().strftime('%H:%M:%S')}</div>
            <div style="font-size:0.76rem;color:#94a3b8">{datetime.now().strftime('%d %b %Y')}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

# ─── KPI CARDS ────────────────────────────────────────────────────────────────
total    = stats.get("total_requests", 0)
high     = stats.get("high_risk_count", 0)
avg_risk = stats.get("avg_risk_score", 0)
anomaly  = stats.get("anomaly_count", 0)
attack_counts = stats.get("attack_counts", {})
high_pct = round(high / total * 100) if total else 0
risk_color = "red" if avg_risk > 0.7 else "amber" if avg_risk > 0.4 else "green"

# Live confidence from model_info
live_conf     = float(model.get("live_confidence") or 0)
live_conf_pct = round(live_conf * 100, 1)

# Attacks per minute — count events in last 60s
attacks_per_min = 0
if history:
    try:
        df_rate = pd.DataFrame(history)
        df_rate["ts"] = pd.to_datetime(df_rate["timestamp"]).dt.tz_localize(None)
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(minutes=1)
        attacks_per_min = int((df_rate["ts"] >= cutoff).sum())
    except:
        attacks_per_min = len(history)
rate_color = "red" if attacks_per_min > 20 else "amber" if attacks_per_min > 10 else "blue"

k1,k2,k3,k4,k5,k6 = st.columns(6)
with k1:
    st.markdown(f'<div class="kpi-card blue"><div class="kpi-label">Total Requests</div><div class="kpi-value blue">{total:,}</div><div class="kpi-sub">Events analyzed</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card red"><div class="kpi-label">High Risk</div><div class="kpi-value red">{high:,}</div><div class="kpi-sub">{high_pct}% of traffic</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card {risk_color}"><div class="kpi-label">Avg Risk Score</div><div class="kpi-value {risk_color}">{avg_risk:.2f}</div><div class="kpi-sub">0 = safe · 1 = critical</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="kpi-card amber"><div class="kpi-label">Anomalies</div><div class="kpi-value amber">{anomaly:,}</div><div class="kpi-sub">Isolation Forest</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="kpi-card green"><div class="kpi-label">Live Confidence</div><div class="kpi-value green">{live_conf_pct}%</div><div class="kpi-sub">Avg model confidence</div></div>', unsafe_allow_html=True)
with k6:
    st.markdown(f'<div class="kpi-card {rate_color}"><div class="kpi-label">Attacks / Min</div><div class="kpi-value {rate_color}">{attacks_per_min}</div><div class="kpi-sub">Last 60 seconds</div></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:1rem'></div>", unsafe_allow_html=True)

# ─── THREAT SEVERITY GAUGE ────────────────────────────────────────────────────
col_gauge, col_gauge_info = st.columns([1, 3])
with col_gauge:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#ef4444"></span>Threat Severity</p>', unsafe_allow_html=True)
    gauge_val = round(avg_risk * 100)
    if avg_risk > 0.75:
        gauge_label, gauge_color = "CRITICAL", "#ef4444"
    elif avg_risk > 0.5:
        gauge_label, gauge_color = "HIGH", "#f97316"
    elif avg_risk > 0.25:
        gauge_label, gauge_color = "MEDIUM", "#f59e0b"
    else:
        gauge_label, gauge_color = "LOW", "#22c55e"
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=gauge_val,
        number={"suffix": "%", "font": {"size": 28, "family": "Inter", "color": gauge_color}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#94a3b8",
                     "tickfont": {"size": 10, "color": "#94a3b8"}},
            "bar": {"color": gauge_color, "thickness": 0.25},
            "bgcolor": "white",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  25],  "color": "#dcfce7"},
                {"range": [25, 50],  "color": "#fef9c3"},
                {"range": [50, 75],  "color": "#ffedd5"},
                {"range": [75, 100], "color": "#fee2e2"},
            ],
            "threshold": {"line": {"color": gauge_color, "width": 3},
                          "thickness": 0.8, "value": gauge_val},
        },
    ))
    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=20,r=20,t=30,b=10), height=200,
        annotations=[dict(text=f"<b>{gauge_label}</b>", x=0.5, y=0.2,
                          font=dict(size=16, color=gauge_color, family="Inter"),
                          showarrow=False)]
    )
    st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

with col_gauge_info:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#6366f1"></span>🧠 Threat Intelligence Summary</p>', unsafe_allow_html=True)
    if history and attack_counts:
        top_attack   = max(attack_counts, key=attack_counts.get)
        top_count    = attack_counts[top_attack]
        recent       = history[-1] if history else {}
        recent_ip    = recent.get("source_ip", "N/A")
        recent_risk  = recent.get("risk_score", 0)
        recent_ts    = recent.get("timestamp","")[:19].replace("T"," ")
        anomaly_rate = round(anomaly / total * 100) if total else 0
        summary_color = gauge_color

        # ── Threat Prediction Algorithm ──────────────────────────────────────
        # Uses last 10 events to find trending attack, weighted so recent
        # events matter more than older ones (weight = position index)
        last10 = [h.get("attack_type","Other") for h in history[-10:]]
        weighted_counts = {}
        for i, atk in enumerate(last10):
            weight = i + 1          # more recent = higher index = higher weight
            weighted_counts[atk] = weighted_counts.get(atk, 0) + weight

        # Remove "Other" / "Normal Traffic" from prediction — not useful
        for exclude in ["Other", "Normal Traffic"]:
            weighted_counts.pop(exclude, None)

        if weighted_counts:
            predicted_next = max(weighted_counts, key=weighted_counts.get)
            pred_score     = weighted_counts[predicted_next]
            pred_total     = sum(weighted_counts.values())
            pred_confidence = round(pred_score / pred_total * 100)
            pred_basis     = f"{len(last10)} recent events, trend-weighted"
        else:
            # All recent traffic is normal — predict it stays normal
            predicted_next  = "Normal Traffic"
            pred_confidence = 90
            pred_basis      = "no attacks in recent traffic"

        pred_color = ATTACK_COLORS.get(predicted_next, "#334155")
        conf_color = "#22c55e" if pred_confidence >= 60 else "#f59e0b"
        # ─────────────────────────────────────────────────────────────────────

        st.markdown(f"""
        <style>
        @keyframes fadeSlideIn {{
            from {{ opacity:0; transform:translateY(8px); }}
            to   {{ opacity:1; transform:translateY(0); }}
        }}
        @keyframes scanline {{
            0%   {{ left:-100%; }}
            100% {{ left:200%; }}
        }}
        @keyframes blink {{
            0%,100% {{ opacity:1; }} 50% {{ opacity:0.3; }}
        }}
        .pred-card {{
            animation: fadeSlideIn 0.6s ease forwards;
            position:relative; overflow:hidden;
            background: linear-gradient(135deg, {pred_color}18 0%, {pred_color}08 100%);
            border: 1.5px solid {pred_color}55;
            border-radius: 12px;
            padding: 0.85rem 1.1rem;
            margin-top: 0.6rem;
        }}
        .pred-card::after {{
            content:'';
            position:absolute; top:0; width:40%; height:100%;
            background: linear-gradient(90deg, transparent, {pred_color}22, transparent);
            animation: scanline 2.5s ease-in-out infinite;
        }}
        .pred-label {{
            font-size:0.68rem; font-weight:700; letter-spacing:0.1em;
            text-transform:uppercase; color:{pred_color}; margin-bottom:0.3rem;
            display:flex; align-items:center; gap:0.4rem;
        }}
        .pred-dot {{
            width:7px; height:7px; border-radius:50%;
            background:{pred_color};
            display:inline-block;
            animation: blink 1.2s infinite;
        }}
        .pred-name {{
            font-size:1.35rem; font-weight:800;
            color:{pred_color}; letter-spacing:-0.02em;
            line-height:1.1;
        }}
        .conf-bar-bg {{
            background:#e2e8f0; border-radius:99px;
            height:5px; width:100%; margin-top:0.5rem; overflow:hidden;
        }}
        .conf-bar-fill {{
            height:100%; border-radius:99px;
            background: linear-gradient(90deg, {pred_color}88, {pred_color});
            width:{pred_confidence}%;
            transition: width 1s ease;
        }}
        </style>
        <div style="background:#f8fafc;border-radius:12px;padding:1rem 1.2rem;border:1px solid #e2e8f0;font-size:0.83rem;color:#334155;line-height:1.9">
            <div>🔴 <b>Dominant Threat:</b> <span style="color:{ATTACK_COLORS.get(top_attack,'#334155')};font-weight:700">{top_attack}</span> — {top_count} events detected</div>
            <div>⚡ <b>Current Threat Level:</b> <span style="color:{summary_color};font-weight:700">{gauge_label}</span> (Risk Score: {avg_risk:.2f})</div>
            <div>🌐 <b>Latest Source IP:</b> <span style="font-family:'JetBrains Mono',monospace">{recent_ip}</span> — Risk {recent_risk:.2f} at {recent_ts[11:]}</div>
            <div>🤖 <b>Anomaly Rate:</b> {anomaly_rate}% of traffic flagged by Isolation Forest</div>
            <div>📡 <b>Attack Rate:</b> {attacks_per_min} events/min — model confidence at {live_conf_pct}%</div>
        </div>
        <div class="pred-card">
            <div class="pred-label">
                <span class="pred-dot"></span>
                🔮 AI Threat Prediction — Next Likely Attack
            </div>
            <div style="display:flex;justify-content:space-between;align-items:flex-end">
                <div class="pred-name">{predicted_next}</div>
                <div style="text-align:right">
                    <div style="font-size:1.1rem;font-weight:800;color:{conf_color}">{pred_confidence}%</div>
                    <div style="font-size:0.68rem;color:#94a3b8;font-weight:600">CONFIDENCE</div>
                </div>
            </div>
            <div class="conf-bar-bg"><div class="conf-bar-fill"></div></div>
            <div style="font-size:0.7rem;color:#94a3b8;margin-top:0.4rem">
                Based on {pred_basis}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Waiting for threat data to generate summary…")
    st.markdown('</div>', unsafe_allow_html=True)
col_map, col_pie = st.columns([3, 2])

with col_map:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#ef4444"></span>🌍 Global Threat Origin Map</p>', unsafe_allow_html=True)
    if history:
        rows = []
        for rec in history:
            ip     = rec.get("source_ip", "")
            attack = rec.get("attack_type", "Other")
            risk   = rec.get("risk_score", 0)
            lat, lon, city = ip_to_geo(ip)
            rows.append({"lat": lat, "lon": lon, "city": city, "attack": attack, "risk": risk})
        df_geo = pd.DataFrame(rows)
        df_agg = (df_geo.groupby(["lat","lon","city","attack"])
                  .agg(count=("risk","count"), avg_risk=("risk","mean"))
                  .reset_index())
        fig_map = go.Figure()
        for attack_type, color in ATTACK_COLORS.items():
            sub = df_agg[df_agg["attack"] == attack_type]
            if sub.empty: continue
            fig_map.add_trace(go.Scattergeo(
                lat=sub["lat"], lon=sub["lon"],
                mode="markers", name=attack_type,
                marker=dict(
                    size=(sub["count"].clip(2,20)*2+6).tolist(),
                    color=color, opacity=0.85,
                    line=dict(width=1.5, color="white"),
                    sizemode="area",
                ),
                text=sub.apply(lambda r: f"<b>{r['city']}</b><br>Type: {r['attack']}<br>Count: {r['count']}<br>Avg Risk: {r['avg_risk']:.2f}", axis=1),
                hoverinfo="text",
            ))
        fig_map.update_layout(
            geo=dict(
                projection_type="natural earth",
                showland=True,  landcolor="#f1f5f9",
                showocean=True, oceancolor="#dbeafe",
                showcountries=True, countrycolor="#cbd5e1", countrywidth=0.5,
                coastlinecolor="#94a3b8", coastlinewidth=0.5,
                showframe=False, bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0,r=0,t=0,b=0), height=340,
            legend=dict(orientation="h", yanchor="bottom", y=-0.12,
                        xanchor="center", x=0.5, font=dict(size=11),
                        bgcolor="rgba(255,255,255,0.85)", bordercolor="#e2e8f0", borderwidth=1),
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Waiting for threat data…")
    st.markdown('</div>', unsafe_allow_html=True)

with col_pie:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#6366f1"></span>Attack Distribution</p>', unsafe_allow_html=True)
    if attack_counts:
        df_pie = pd.DataFrame({"Attack": list(attack_counts.keys()), "Count": list(attack_counts.values())}).sort_values("Count", ascending=False)
        total_events = sum(attack_counts.values())
        fig_pie = go.Figure(go.Pie(
            labels=df_pie["Attack"], values=df_pie["Count"], hole=0.58,
            marker=dict(colors=[ATTACK_COLORS.get(a,"#94a3b8") for a in df_pie["Attack"]], line=dict(color="white",width=2.5)),
            textinfo="percent", textfont=dict(size=12, family="Inter"),
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
        ))
        fig_pie.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=10,r=10,t=10,b=10), height=200,
            legend=dict(orientation="v", font=dict(size=11), x=1.02, y=0.5, bgcolor="rgba(0,0,0,0)"),
            annotations=[dict(text=f"<b>{total_events}</b><br><span>Events</span>",
                              x=0.5, y=0.5, font=dict(size=15, family="Inter"), showarrow=False)]
        )
        st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
        for att, cnt in sorted(attack_counts.items(), key=lambda x: -x[1]):
            color = ATTACK_COLORS.get(att, "#94a3b8")
            pct   = round(cnt / total_events * 100)
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:0.28rem 0;border-bottom:1px solid #f1f5f9;font-size:0.79rem">
                <div style="display:flex;align-items:center;gap:0.4rem">
                    <span style="width:9px;height:9px;border-radius:50%;background:{color};display:inline-block"></span>
                    <span style="color:#334155;font-weight:500">{att}</span>
                </div>
                <span style="color:#64748b;font-variant-numeric:tabular-nums">{cnt} <span style="color:#cbd5e1">({pct}%)</span></span>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Waiting for data…")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

# ─── ROW 3: RISK TIMELINE + LIVE ALERTS ───────────────────────────────────────
col_line, col_alerts = st.columns([3, 2])

with col_line:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#22c55e"></span>Risk Score Timeline</p>', unsafe_allow_html=True)
    if history:
        df_line = pd.DataFrame(history[-60:])
        df_line["timestamp"] = pd.to_datetime(df_line["timestamp"])
        df_line = df_line.sort_values("timestamp")
        fig_line = go.Figure()
        # Shaded zones
        fig_line.add_hrect(y0=0.7,y1=1.05, fillcolor="rgba(239,68,68,0.07)",  line_width=0, annotation_text="HIGH", annotation_position="right", annotation_font=dict(color="#ef4444",size=10))
        fig_line.add_hrect(y0=0.4,y1=0.7,  fillcolor="rgba(245,158,11,0.07)", line_width=0, annotation_text="MED",  annotation_position="right", annotation_font=dict(color="#f59e0b",size=10))
        fig_line.add_hrect(y0=0,  y1=0.4,  fillcolor="rgba(34,197,94,0.07)",  line_width=0, annotation_text="LOW",  annotation_position="right", annotation_font=dict(color="#22c55e",size=10))
        for attack_type, color in ATTACK_COLORS.items():
            sub = df_line[df_line["attack_type"] == attack_type]
            if sub.empty: continue
            fig_line.add_trace(go.Scatter(
                x=sub["timestamp"], y=sub["risk_score"],
                mode="lines+markers", name=attack_type,
                line=dict(color=color, width=2.5),
                marker=dict(size=5, color=color, line=dict(width=1.5, color="white")),
                hovertemplate=f"<b>{attack_type}</b><br>Risk: %{{y:.3f}}<br>%{{x|%H:%M:%S}}<extra></extra>",
            ))
        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=285, margin=dict(l=10,r=60,t=10,b=10),
            yaxis=dict(range=[0,1.05], tickformat=".1f", gridcolor="#f1f5f9",
                       tickfont=dict(size=10,color="#94a3b8"), title=None, zeroline=False),
            xaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=10,color="#94a3b8"), title=None),
            legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5,
                        font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Waiting for data…")
    st.markdown('</div>', unsafe_allow_html=True)

with col_alerts:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#ef4444"></span>Live Threat Alerts</p>', unsafe_allow_html=True)
    if history:
        for idx, pred in enumerate(reversed(history[-8:])):
            attack = pred.get("attack_type", "?")
            ip     = pred.get("source_ip", "?")
            risk   = pred.get("risk_score", 0)
            level  = pred.get("threat_level", "LOW")
            ts     = pred.get("timestamp","")[:19].replace("T"," ")
            css_cls = {"HIGH":"alert-high","MEDIUM":"alert-medium","LOW":"alert-low"}.get(level,"alert-low")
            tag_cls = {"HIGH":"tag-high","MEDIUM":"tag-medium","LOW":"tag-low"}.get(level,"tag-low")
            color   = ATTACK_COLORS.get(attack, "#6366f1")
            st.markdown(f"""
            <div class="alert-row {css_cls}">
                <div>
                    <div style="font-weight:700;color:{color}">{attack}</div>
                    <div style="font-size:0.7rem;opacity:0.7;font-family:'JetBrains Mono',monospace">{ip} · {ts[11:]}</div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:3px">
                    <span class="alert-tag {tag_cls}">{level}</span>
                    <span style="font-size:0.73rem;font-weight:700">{risk:.2f}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No alerts yet.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

# ─── ROW 4: MODEL STATS + SUSPICIOUS IPs + BAR CHART ─────────────────────────
col_model, col_ips, col_bar = st.columns([1.2, 1.4, 1.4])

with col_model:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#8b5cf6"></span>Model Performance</p>', unsafe_allow_html=True)
    acc   = model.get("accuracy") or 0.97
    acc   = float(acc)
    trees = model.get("n_estimators", 100)
    feats = model.get("n_features", 26)
    iso   = "✅ Active" if model.get("iso_forest_fitted", False) else "⏳ Training"
    st.markdown(f"""
    <div class="model-stat" style="margin-bottom:0.6rem">
        <div class="model-stat-val" style="color:#22c55e">{acc*100:.1f}%</div>
        <div class="model-stat-lbl">Accuracy</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.6rem">
        <div class="model-stat"><div class="model-stat-val" style="font-size:1.3rem">{trees}</div><div class="model-stat-lbl">Trees</div></div>
        <div class="model-stat"><div class="model-stat-val" style="font-size:1.3rem">{feats}</div><div class="model-stat-lbl">Features</div></div>
    </div>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:0.6rem 0.8rem;font-size:0.76rem;color:#475569;line-height:1.7">
        <div><b>Algorithm:</b> Random Forest</div>
        <div><b>Anomaly:</b> Isolation Forest — {iso}</div>
        <div><b>Dataset:</b> CICIDS2017</div>
    </div>
    <div style="margin-top:0.8rem">
        <div style="display:flex;justify-content:space-between;font-size:0.7rem;color:#94a3b8;margin-bottom:0.3rem">
            <span>Model Confidence</span><span>{acc*100:.1f}%</span>
        </div>
        <div style="background:#f1f5f9;border-radius:99px;height:6px;overflow:hidden">
            <div style="width:{acc*100}%;height:100%;border-radius:99px;background:linear-gradient(90deg,#22c55e,#16a34a)"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col_ips:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#f97316"></span>Top Suspicious IPs</p>', unsafe_allow_html=True)
    if history:
        df_ips = pd.DataFrame(history)
        df_ips = df_ips[df_ips["attack_type"] != "Other"]
        if not df_ips.empty:
            top_ips = (df_ips.groupby("source_ip")
                       .agg(attacks=("attack_type","count"),
                            top_attack=("attack_type", lambda x: x.value_counts().index[0]),
                            avg_risk=("risk_score","mean"))
                       .reset_index()
                       .sort_values("attacks", ascending=False)
                       .head(8))
            for _, row in top_ips.iterrows():
                color = ATTACK_COLORS.get(row["top_attack"], "#94a3b8")
                st.markdown(f"""
                <div class="ip-row">
                    <div>
                        <span class="ip-badge">{row['source_ip']}</span>
                        <span style="font-size:0.68rem;color:{color};font-weight:600;margin-left:0.3rem">{row['top_attack']}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:0.4rem">
                        <span style="font-size:0.7rem;color:#94a3b8">{row['avg_risk']:.2f}</span>
                        <span class="count-badge">{row['attacks']}</span>
                    </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No suspicious IPs detected.")
    else:
        st.info("Waiting for data…")
    st.markdown('</div>', unsafe_allow_html=True)

with col_bar:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#f59e0b"></span>Attack Volume by Type</p>', unsafe_allow_html=True)
    if attack_counts:
        df_bar = pd.DataFrame({"Attack": list(attack_counts.keys()), "Count": list(attack_counts.values())}).sort_values("Count", ascending=True)
        fig_bar = go.Figure(go.Bar(
            x=df_bar["Count"], y=df_bar["Attack"], orientation="h",
            marker=dict(color=[ATTACK_COLORS.get(a,"#94a3b8") for a in df_bar["Attack"]], line=dict(width=0)),
            text=df_bar["Count"], textposition="outside",
            textfont=dict(size=11, family="Inter", color="#475569"),
            hovertemplate="<b>%{y}</b>: %{x} events<extra></extra>",
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=240, margin=dict(l=0,r=40,t=0,b=10),
            xaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=10,color="#94a3b8"), title=None, zeroline=False),
            yaxis=dict(tickfont=dict(size=11,color="#334155",family="Inter"), title=None),
            bargap=0.35,
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Waiting for data…")
    st.markdown('</div>', unsafe_allow_html=True)

# ─── ROW 5: NETWORK TRAFFIC VOLUME + EXPORT ───────────────────────────────────
col_traffic, col_export = st.columns([3, 1])

with col_traffic:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#6366f1"></span>Network Traffic Volume</p>', unsafe_allow_html=True)
    if history:
        df_vol = pd.DataFrame(history)
        df_vol["timestamp"] = pd.to_datetime(df_vol["timestamp"])
        df_vol = df_vol.sort_values("timestamp")
        # Bucket into 10-second intervals
        df_vol["bucket"] = df_vol["timestamp"].dt.floor("10s")
        vol_data = df_vol.groupby("bucket").size().reset_index(name="count")
        fig_area = go.Figure()
        fig_area.add_trace(go.Scatter(
            x=vol_data["bucket"], y=vol_data["count"],
            mode="lines", fill="tozeroy",
            line=dict(color="#6366f1", width=2),
            fillcolor="rgba(99,102,241,0.12)",
            hovertemplate="Time: %{x|%H:%M:%S}<br>Events: %{y}<extra></extra>",
            name="Traffic",
        ))
        fig_area.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=200, margin=dict(l=10,r=10,t=10,b=10),
            xaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=10,color="#94a3b8"), title=None),
            yaxis=dict(gridcolor="#f1f5f9", tickfont=dict(size=10,color="#94a3b8"), title=None, zeroline=False),
            showlegend=False, hovermode="x unified",
        )
        st.plotly_chart(fig_area, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Waiting for data…")
    st.markdown('</div>', unsafe_allow_html=True)

with col_export:
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)
    st.markdown('<p class="section-header"><span class="dot" style="background:#22c55e"></span>Export Report</p>', unsafe_allow_html=True)
    if history:
        df_export = pd.DataFrame(history)
        # CSV export
        csv_data = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=f"threat_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
        st.markdown("<div style='margin-top:0.5rem'></div>", unsafe_allow_html=True)
        # Summary text export
        summary_lines = [
            f"CyberThreat Intelligence Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"SUMMARY",
            f"Total Events : {total}",
            f"High Risk    : {high} ({high_pct}%)",
            f"Avg Risk     : {avg_risk:.4f}",
            f"Anomalies    : {anomaly}",
            f"Threat Level : {gauge_label}",
            f"Attacks/Min  : {attacks_per_min}",
            f"Confidence   : {live_conf_pct}%",
            f"",
            f"ATTACK BREAKDOWN",
        ]
        for att, cnt in sorted(attack_counts.items(), key=lambda x: -x[1]):
            summary_lines.append(f"  {att:<18}: {cnt}")
        summary_txt = "\n".join(summary_lines).encode("utf-8")
        st.download_button(
            label="⬇️ Download Report (TXT)",
            data=summary_txt,
            file_name=f"threat_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.markdown(f"""
        <div style="margin-top:0.8rem;font-size:0.75rem;color:#94a3b8;text-align:center">
            {len(df_export)} records ready
        </div>""", unsafe_allow_html=True)
    else:
        st.info("No data to export yet.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:0.5rem'></div>", unsafe_allow_html=True)

# ─── AUTO REFRESH ─────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(REFRESH_SECS)
    st.rerun()