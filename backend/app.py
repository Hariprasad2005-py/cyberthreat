"""
app.py
------
Flask API Backend
- Accepts POST /predict with network traffic features
- Returns attack_type + risk_score + is_anomaly
- Isolation Forest for anomaly detection
- Exposes GET /history, /stats, /health, /model_info
- Auto-simulator runs in background using clean_dataset.csv
"""

import os
import json
import time
import random
import threading
import numpy as np
import joblib
import pandas as pd
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
from sklearn.ensemble import IsolationForest

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH       = os.path.join(BASE_DIR, "model", "cyber_model.pkl")
SCALER_PATH      = os.path.join(BASE_DIR, "model", "scaler.pkl")
ENCODER_PATH     = os.path.join(BASE_DIR, "model", "label_encoder.pkl")
DATASET_PATH     = os.path.join(BASE_DIR, "archive", "clean_dataset.csv")
META_PATH        = os.path.join(BASE_DIR, "model", "model_meta.json")
BLOCKED_IPS_FILE = os.path.join(BASE_DIR, "blocked_ips.json")

# ─── APP SETUP ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

prediction_history = []

# ─── BLOCKED IPs (persistent) ─────────────────────────────────────────────────
def load_blocked_ips():
    if os.path.exists(BLOCKED_IPS_FILE):
        try:
            with open(BLOCKED_IPS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_blocked_ips(ips):
    try:
        with open(BLOCKED_IPS_FILE, "w") as f:
            json.dump(ips, f)
    except Exception as e:
        print(f"[WARN] Could not save blocked IPs: {e}")

blocked_ips = load_blocked_ips()
print(f"[INFO] Loaded {len(blocked_ips)} blocked IPs from disk.")

# ─── LOAD MODEL ───────────────────────────────────────────────────────────────
def load_artifacts():
    if not os.path.exists(MODEL_PATH):
        print("[WARN] Model not found.")
        return None, None, None
    clf     = joblib.load(MODEL_PATH)
    scaler  = joblib.load(SCALER_PATH)
    encoder = joblib.load(ENCODER_PATH)
    print("[INFO] Model, scaler and encoder loaded.")
    return clf, scaler, encoder

clf, scaler, encoder = load_artifacts()

# ─── ISOLATION FOREST ─────────────────────────────────────────────────────────
isolation_forest  = None
iso_forest_fitted = False

def fit_isolation_forest(X):
    global isolation_forest, iso_forest_fitted
    print("[INFO] Fitting Isolation Forest...")
    isolation_forest = IsolationForest(contamination=0.05, random_state=42, n_estimators=100)
    isolation_forest.fit(X)
    iso_forest_fitted = True
    print("[INFO] Isolation Forest fitted.")

def load_and_fit_iso_forest():
    if not os.path.exists(DATASET_PATH):
        print("[WARN] Dataset not found for Isolation Forest.")
        return
    try:
        df        = pd.read_csv(DATASET_PATH)
        label_col = [c for c in df.columns if "label" in c.lower()][0]
        feat_cols = [c for c in df.columns if c != label_col]
        X         = df[feat_cols].values
        if scaler is not None:
            expected = scaler.n_features_in_
            if X.shape[1] < expected:
                X = np.pad(X, ((0, 0), (0, expected - X.shape[1])))
            elif X.shape[1] > expected:
                X = X[:, :expected]
            X = scaler.transform(X)
        fit_isolation_forest(X)
    except Exception as e:
        print(f"[WARN] Could not fit Isolation Forest: {e}")

# ─── RISK MAP ─────────────────────────────────────────────────────────────────
RISK_MAP = {
    "Other"  : 0.05,
    "DDoS"   : 0.92,
    "Botnet" : 0.85,
}

IP_POOLS = {
    "Other"  : [f"10.0.0.{i}"     for i in range(1, 50)],
    "DDoS"   : [f"203.0.{i}.1"    for i in range(1, 20)],
    "Botnet" : [f"198.51.100.{i}" for i in range(1, 20)],
}

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def compute_risk(attack_type, proba):
    base = RISK_MAP.get(attack_type, 0.5)
    return round(min(1.0, base * 0.6 + proba * 0.4), 4)

def preprocess_input(data):
    vec      = np.array(list(data.values()), dtype=float).reshape(1, -1)
    expected = scaler.n_features_in_
    if vec.shape[1] < expected:
        vec = np.pad(vec, ((0, 0), (0, expected - vec.shape[1])))
    elif vec.shape[1] > expected:
        vec = vec[:, :expected]
    return scaler.transform(vec)

# ─── AUTO SIMULATOR ───────────────────────────────────────────────────────────
def load_dataset_for_sim():
    if not os.path.exists(DATASET_PATH):
        print(f"[SIMULATOR] Dataset not found at {DATASET_PATH}")
        return None, None, None
    df        = pd.read_csv(DATASET_PATH)
    label_col = [c for c in df.columns if "label" in c.lower()][0]
    feat_cols = [c for c in df.columns if c != label_col]
    classes   = df[label_col].unique().tolist()
    class_groups = {}
    for cls in classes:
        rows = df[df[label_col] == cls][feat_cols]
        class_groups[cls] = rows.values.tolist()
    print(f"[SIMULATOR] Dataset loaded: {len(df)} rows, classes: {classes}")
    return class_groups, feat_cols, classes

def auto_simulate():
    print("[SIMULATOR] Starting in 2 seconds...")
    time.sleep(2)
    class_groups, feature_cols, classes = load_dataset_for_sim()
    if class_groups is None:
        print("[SIMULATOR] Could not load dataset. Stopped.")
        return
    print("[SIMULATOR] Running! Sending traffic every 2 seconds...")
    port    = int(os.environ.get("PORT", 5000))
    api_url = f"http://127.0.0.1:{port}/predict"
    while True:
        try:
            attack_class = random.choice(classes)
            rows         = class_groups[attack_class]
            row          = random.choice(rows)
            features     = {feature_cols[i]: round(float(row[i]), 6) for i in range(len(feature_cols))}
            ip_pool      = IP_POOLS.get(attack_class, [f"192.168.1.{random.randint(1,254)}"])
            features["source_ip"] = random.choice(ip_pool)
            requests.post(api_url, json=features, timeout=5)
            time.sleep(2)
        except Exception as e:
            print(f"[SIMULATOR] Error: {e}")
            time.sleep(5)

# ─── ROUTES ───────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service"  : "CyberThreat Detection API",
        "version"  : "2.0.0",
        "endpoints": ["/predict", "/history", "/stats", "/health", "/model_info",
                      "/blocked_ips", "/block_ip", "/unblock_ip"],
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status"      : "ok",
        "model_loaded": clf is not None,
        "timestamp"   : datetime.utcnow().isoformat(),
    })

@app.route("/model_info", methods=["GET"])
def model_info():
    # ── Live confidence calculated from every prediction in history ───────────
    avg_confidence = 0.0
    min_confidence = 0.0
    max_confidence = 0.0
    total_analysed = len(prediction_history)

    if prediction_history:
        confidences    = [p.get("confidence", 0) for p in prediction_history[-100:]]
        avg_confidence = round(sum(confidences) / len(confidences), 4)
        min_confidence = round(min(confidences), 4)
        max_confidence = round(max(confidences), 4)

    # ── Real trained accuracy — read from model_meta.json saved by train_model.py
    trained_accuracy = None
    try:
        with open(META_PATH) as f:
            trained_accuracy = json.load(f).get("accuracy")
    except:
        pass

    info = {
        "accuracy"             : trained_accuracy,
        "live_confidence"      : avg_confidence,
        "min_confidence"       : min_confidence,
        "max_confidence"       : max_confidence,
        "total_analysed"       : total_analysed,
        "n_estimators"         : clf.n_estimators if clf is not None else 100,
        "n_features"           : int(scaler.n_features_in_) if scaler is not None else 26,
        "anomaly_contamination": 0.05,
        "iso_forest_fitted"    : iso_forest_fitted,
        "model_type"           : "RandomForestClassifier + IsolationForest",
        "classes"              : list(encoder.classes_) if encoder is not None else [],
    }

    return jsonify(info)

@app.route("/predict", methods=["POST"])
def predict():
    if clf is None:
        return jsonify({"error": "Model not loaded."}), 503

    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "Empty request body."}), 400

    source_ip = body.pop("source_ip", f"192.168.{random.randint(1,254)}.{random.randint(1,254)}")

    try:
        X         = preprocess_input(body)
        pred_idx  = clf.predict(X)[0]
        proba_max = float(clf.predict_proba(X)[0].max())
        attack    = encoder.inverse_transform([pred_idx])[0]
        risk      = compute_risk(attack, proba_max)

        is_anomaly = False
        if iso_forest_fitted and isolation_forest is not None:
            iso_pred   = isolation_forest.predict(X)
            is_anomaly = bool(iso_pred[0] == -1)

        result = {
            "attack_type" : attack,
            "risk_score"  : risk,
            "confidence"  : round(proba_max, 4),
            "source_ip"   : source_ip,
            "timestamp"   : datetime.utcnow().isoformat(),
            "threat_level": "HIGH" if risk > 0.7 else "MEDIUM" if risk > 0.4 else "LOW",
            "is_anomaly"  : is_anomaly,
        }

        prediction_history.append(result)
        if len(prediction_history) > 200:
            prediction_history.pop(0)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history", methods=["GET"])
def history():
    limit = int(request.args.get("limit", 50))
    return jsonify(prediction_history[-limit:]), 200

@app.route("/stats", methods=["GET"])
def stats():
    if not prediction_history:
        return jsonify({
            "total_requests" : 0,
            "attack_counts"  : {},
            "avg_risk_score" : 0,
            "high_risk_count": 0,
            "anomaly_count"  : 0,
        })

    attack_counts = {}
    total_risk    = 0.0
    high_risk     = 0
    anomaly_count = 0

    for p in prediction_history:
        attack = p["attack_type"]
        attack_counts[attack] = attack_counts.get(attack, 0) + 1
        total_risk  += p["risk_score"]
        if p["risk_score"] > 0.7:
            high_risk += 1
        if p.get("is_anomaly", False):
            anomaly_count += 1

    return jsonify({
        "total_requests" : len(prediction_history),
        "attack_counts"  : attack_counts,
        "avg_risk_score" : round(total_risk / len(prediction_history), 4),
        "high_risk_count": high_risk,
        "anomaly_count"  : anomaly_count,
    }), 200

@app.route("/blocked_ips", methods=["GET"])
def get_blocked_ips():
    return jsonify(blocked_ips), 200

@app.route("/block_ip", methods=["POST"])
def block_ip():
    data = request.get_json(force=True)
    ip   = data.get("ip")
    if ip and ip not in blocked_ips:
        blocked_ips.append(ip)
        save_blocked_ips(blocked_ips)
    return jsonify({"status": "blocked", "ip": ip, "total_blocked": len(blocked_ips)}), 200

@app.route("/unblock_ip", methods=["POST"])
def unblock_ip():
    data = request.get_json(force=True)
    ip   = data.get("ip")
    if ip in blocked_ips:
        blocked_ips.remove(ip)
        save_blocked_ips(blocked_ips)
    return jsonify({"status": "unblocked", "ip": ip, "total_blocked": len(blocked_ips)}), 200
@app.route("/reset", methods=["POST"])
def reset():
    global prediction_history
    prediction_history = []
    return jsonify({"status": "reset"}), 200
# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  CyberThreat Detection API v2.0 — Starting ...")
    print("=" * 50)

    t1 = threading.Thread(target=load_and_fit_iso_forest, daemon=True)
    t1.start()

    t2 = threading.Thread(target=auto_simulate, daemon=True)
    t2.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)