"""
app.py
------
Step 4: Flask API Backend
- Accepts POST /predict with network traffic features
- Returns attack_type + risk_score
- Exposes GET /history for recent predictions
- Exposes GET /stats for dashboard metrics
"""

import os
import sys
import json
import time
import random
import numpy as np
import joblib
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# ─── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH   = os.path.join(BASE_DIR, "model", "cyber_model.pkl")
SCALER_PATH  = os.path.join(BASE_DIR, "model", "scaler.pkl")
ENCODER_PATH = os.path.join(BASE_DIR, "model", "label_encoder.pkl")

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

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def compute_risk(attack_type: str, proba: float) -> float:
    base = RISK_MAP.get(attack_type, 0.5)
    # Blend base risk with model confidence
    return round(min(1.0, base * 0.6 + proba * 0.4), 4)


def preprocess_input(data: dict) -> np.ndarray:
    vec = np.array(list(data.values()), dtype=float).reshape(1, -1)
    expected = scaler.n_features_in_
    if vec.shape[1] < expected:
        vec = np.pad(vec, ((0, 0), (0, expected - vec.shape[1])))
    elif vec.shape[1] > expected:
        vec = vec[:, :expected]
    return scaler.transform(vec)


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
    """
    POST /predict
    Body (JSON): { "feature_0": 1.2, "feature_1": 0.5, ..., "source_ip": "192.168.1.1" }
    Returns:     { "attack_type": "DDoS", "risk_score": 0.92, "source_ip": "...", "timestamp": "..." }
    """
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

        # Store in history (keep last 200)
        prediction_history.append(result)
        if len(prediction_history) > 200:
            prediction_history.pop(0)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/history", methods=["GET"])
def history():
    """GET /history — returns last N predictions (default 50)."""
    limit = int(request.args.get("limit", 50))
    return jsonify(prediction_history[-limit:]), 200


@app.route("/stats", methods=["GET"])
def stats():
    """GET /stats — aggregated metrics for dashboard."""
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
    print("  http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)