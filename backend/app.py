"""
app.py
------
Step 4: Flask API Backend
- Accepts POST /predict with network traffic features
- Returns attack_type + risk_score
- Exposes GET /history for recent predictions
- Exposes GET /stats for dashboard metrics
- Auto-simulator runs in background using clean_dataset.csv
"""

import os
import sys
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

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH   = os.path.join(BASE_DIR, "model", "cyber_model.pkl")
SCALER_PATH  = os.path.join(BASE_DIR, "model", "scaler.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "model", "label_encoder.pkl")
DATASET_PATH = os.path.join(BASE_DIR, "archive", "clean_dataset.csv")

# ─── APP SETUP ────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# In-memory prediction history (last 200 records)
prediction_history = []

# ─── LOAD MODEL ───────────────────────────────────────────────────────────────
def load_artifacts():
    if not os.path.exists(MODEL_PATH):
        print("[WARN] Model not found. Run: python model/train_model.py")
        return None, None, None
    clf     = joblib.load(MODEL_PATH)
    scaler  = joblib.load(SCALER_PATH)
    encoder = joblib.load(ENCODER_PATH)
    print("[INFO] Model, scaler and encoder loaded.")
    return clf, scaler, encoder

clf, scaler, encoder = load_artifacts()

# Risk score thresholds per attack class
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

def compute_risk(attack_type: str, proba: float) -> float:
    base = RISK_MAP.get(attack_type, 0.5)
    return round(min(1.0, base * 0.6 + proba * 0.4), 4)


def preprocess_input(data: dict) -> np.ndarray:
    vec = np.array(list(data.values()), dtype=float).reshape(1, -1)
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

    df = pd.read_csv(DATASET_PATH)
    label_col = [c for c in df.columns if "label" in c.lower()][0]
    feature_cols = [c for c in df.columns if c != label_col]
    classes = df[label_col].unique().tolist()

    class_groups = {}
    for cls in classes:
        rows = df[df[label_col] == cls][feature_cols]
        class_groups[cls] = rows.values.tolist()

    print(f"[SIMULATOR] Dataset loaded: {len(df)} rows, classes: {classes}")
    return class_groups, feature_cols, classes


def auto_simulate():
    """Reads from clean_dataset.csv and sends traffic to /predict every 2s."""
    print("[SIMULATOR] Starting in 15 seconds...")
    time.sleep(15)  # wait for Flask to fully start

    class_groups, feature_cols, classes = load_dataset_for_sim()
    if class_groups is None:
        print("[SIMULATOR] Could not load dataset. Simulator stopped.")
        return

    print("[SIMULATOR] Running! Sending traffic every 2 seconds...")
    port = int(os.environ.get("PORT", 5000))
    api_url = f"http://127.0.0.1:{port}/predict"

    while True:
        try:
            # Pick a random class
            attack_class = random.choice(classes)
            rows = class_groups[attack_class]
            row  = random.choice(rows)

            features = {feature_cols[i]: round(float(row[i]), 6) for i in range(len(feature_cols))}
            ip_pool  = IP_POOLS.get(attack_class, [f"192.168.1.{random.randint(1,254)}"])
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
        "service": "CyberThreat Detection API",
        "version": "1.0.0",
        "endpoints": ["/predict", "/history", "/stats", "/health"],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status"       : "ok",
        "model_loaded" : clf is not None,
        "timestamp"    : datetime.utcnow().isoformat(),
    })


@app.route("/predict", methods=["POST"])
def predict():
    if clf is None:
        return jsonify({"error": "Model not loaded. Run train_model.py first."}), 503

    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "Empty request body."}), 400

    source_ip = body.pop("source_ip", f"192.168.{random.randint(1,254)}.{random.randint(1,254)}")

    try:
        X = preprocess_input(body)
        pred_idx  = clf.predict(X)[0]
        proba_max = float(clf.predict_proba(X)[0].max())
        attack    = encoder.inverse_transform([pred_idx])[0]
        risk      = compute_risk(attack, proba_max)

        result = {
            "attack_type" : attack,
            "risk_score"  : risk,
            "confidence"  : round(proba_max, 4),
            "source_ip"   : source_ip,
            "timestamp"   : datetime.utcnow().isoformat(),
            "threat_level": "HIGH" if risk > 0.7 else "MEDIUM" if risk > 0.4 else "LOW",
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
            "total_requests"   : 0,
            "attack_counts"    : {},
            "avg_risk_score"   : 0,
            "high_risk_count"  : 0,
        })

    attack_counts = {}
    total_risk    = 0.0
    high_risk     = 0

    for p in prediction_history:
        attack = p["attack_type"]
        attack_counts[attack] = attack_counts.get(attack, 0) + 1
        total_risk += p["risk_score"]
        if p["risk_score"] > 0.7:
            high_risk += 1

    return jsonify({
        "total_requests"  : len(prediction_history),
        "attack_counts"   : attack_counts,
        "avg_risk_score"  : round(total_risk / len(prediction_history), 4),
        "high_risk_count" : high_risk,
    }), 200


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  CyberThreat Detection API — Starting …")
    print("=" * 50)

    # Start background simulator
    t = threading.Thread(target=auto_simulate, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)