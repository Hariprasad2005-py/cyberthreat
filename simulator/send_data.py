"""
send_data.py
------------
Step 6: Live Traffic Simulation
- Reads real rows from archive/clean_dataset.csv
- Sends them to the Flask API (/predict)
- Guarantees a mix of all attack classes
- Prints live results to terminal

Usage:
    python simulator/send_data.py              # default: 50 packets, 1s delay
    python simulator/send_data.py --n 100      # 100 packets
    python simulator/send_data.py --delay 0.5  # 0.5s between packets
    python simulator/send_data.py --burst       # send as fast as possible
"""

import argparse
import random
import time
import requests
import pandas as pd
import os

# ─── CONFIG ───────────────────────────────────────────────────────────────────
API_BASE = "https://cyberthreat-api.onrender.com"DATASET_PATH = "archive/dataset.csv"

IP_POOLS = {
    "Other"  : [f"10.0.0.{i}"     for i in range(1, 50)],
    "DDoS"   : [f"203.0.{i}.{j}"  for i in range(1, 10) for j in range(1, 10)],
    "Botnet" : [f"198.51.100.{i}" for i in range(1, 20)],
}


# ─── LOAD DATASET ─────────────────────────────────────────────────────────────

def load_dataset():
    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] Dataset not found at {DATASET_PATH}")
        print("[INFO]  Run: python model/preprocess.py first")
        exit(1)

    df = pd.read_csv(DATASET_PATH)

    # Find label column
    label_col = [c for c in df.columns if "label" in c.lower()][0]

    # Feature columns = all except label
    feature_cols = [c for c in df.columns if c != label_col]

    classes = df[label_col].unique().tolist()
    print(f"[INFO] Dataset loaded: {len(df)} rows")
    print(f"[INFO] Classes found : {classes}")
    print(f"[INFO] Features      : {len(feature_cols)}")

    # Group rows by class
    class_groups = {}
    for cls in classes:
        rows = df[df[label_col] == cls][feature_cols]
        class_groups[cls] = rows.values.tolist()
        print(f"[INFO]   {cls:<20}: {len(rows)} rows")

    return class_groups, feature_cols, classes


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def generate_traffic(class_groups, classes, feature_cols, attack):
    """Pick a real row from dataset for the given attack class."""
    rows = class_groups[attack]
    row  = random.choice(rows)
    features = {feature_cols[i]: round(float(row[i]), 6) for i in range(len(feature_cols))}
    ip_pool = IP_POOLS.get(attack, [f"192.168.1.{random.randint(1,254)}"])
    features["source_ip"] = random.choice(ip_pool)
    return features


def send_packet(features):
    try:
        r = requests.post(API_URL, json=features, timeout=5)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"[ERROR] API returned {r.status_code}: {r.text}")
            return None
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to API. Is backend/app.py running?")
        return None


def print_result(pred, packet_num, sent_class):
    attack = pred.get("attack_type", "?")
    risk   = pred.get("risk_score", 0)
    level  = pred.get("threat_level", "?")
    ip     = pred.get("source_ip", "?")
    ts     = pred.get("timestamp", "")[:19].replace("T", " ")
    icon   = "✅" if attack == "Other" else "🚨"
    bar    = "█" * int(risk * 20) + "░" * (20 - int(risk * 20))
    match  = "✓" if attack == sent_class else "✗"

    print(f"\n[{packet_num:04d}] {icon} {ts}")
    print(f"  Sent     : {sent_class:<12}  →  Predicted: {attack} {match}")
    print(f"  Threat   : {level}")
    print(f"  Source IP: {ip}")
    print(f"  Risk     : {risk:.4f}  [{bar}]")


# ─── MAIN SIMULATION LOOP ─────────────────────────────────────────────────────

def simulate(n=50, delay=1.0, burst=False):
    print("=" * 55)
    print("  CyberThreat — Traffic Simulator (Real Data)")
    print(f"  Sending {n} packets to {API_URL}")
    print(f"  Delay: {'burst' if burst else f'{delay}s'}")
    print("=" * 55)

    class_groups, feature_cols, classes = load_dataset()

    # Build round-robin sequence to guarantee every class is represented
    per_class = max(1, n // len(classes))
    sequence  = []
    for cls in classes:
        sequence.extend([cls] * per_class)
    while len(sequence) < n:
        sequence.append(random.choice(classes))
    random.shuffle(sequence)
    sequence = sequence[:n]

    mix = {c: sequence.count(c) for c in classes}
    print(f"\n[INFO] Sending mix: {mix}\n")

    stats  = {}
    errors = 0

    for i, attack_class in enumerate(sequence, 1):
        features = generate_traffic(class_groups, classes, feature_cols, attack_class)
        pred     = send_packet(features)

        if pred:
            print_result(pred, i, attack_class)
            predicted       = pred.get("attack_type", "Other")
            stats[predicted] = stats.get(predicted, 0) + 1
        else:
            errors += 1
            if errors >= 3:
                print("\n[ABORT] Too many connection errors. Stopping.")
                break

        if not burst:
            time.sleep(delay)

    print("\n" + "=" * 55)
    print("  SIMULATION SUMMARY (Predictions)")
    print("=" * 55)
    for attack, count in stats.items():
        print(f"  {attack:<18}: {count:>4}  {'█' * count}")
    print(f"  Errors             : {errors}")
    print("=" * 55)


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CyberThreat Traffic Simulator")
    parser.add_argument("--n",     type=int,   default=50,  help="Number of packets")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between packets")
    parser.add_argument("--burst", action="store_true",     help="No delay")
    args = parser.parse_args()
    simulate(n=args.n, delay=args.delay, burst=args.burst)