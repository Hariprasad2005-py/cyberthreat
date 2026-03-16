"""
preprocess.py
-------------
Step 1 & 2: Data Preparation + Preprocessing
- Load CICIDS2017 CSV dataset
- Clean missing values
- Encode labels
- Scale features
- Split into train/test sets
- Save clean_dataset.csv
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os

# ─── CONFIG ───────────────────────────────────────────────────────────────────
DATASET_PATH = "archive/dataset.csv"   # Put your CICIDS2017 CSV here
CLEAN_CSV    = "archive/clean_dataset.csv"
SCALER_PATH  = "model/scaler.pkl"
ENCODER_PATH = "model/label_encoder.pkl"

# Known attack labels in CICIDS2017
ATTACK_LABELS = {
    "BENIGN"      : "Normal Traffic",
    "DDoS"        : "DDoS",
    "PortScan"    : "Port Scan",
    "FTP-Patator" : "Brute Force",
    "SSH-Patator" : "Brute Force",
    "Bot"         : "Botnet",
}

# Features selected from CICIDS2017 (strip-safe names)
SELECTED_FEATURES = [
    "Destination Port", "Flow Duration", "Total Fwd Packets",
    "Total Backward Packets", "Total Length of Fwd Packets",
    "Total Length of Bwd Packets", "Fwd Packet Length Max",
    "Fwd Packet Length Min", "Fwd Packet Length Mean",
    "Bwd Packet Length Max", "Bwd Packet Length Min",
    "Bwd Packet Length Mean", "Flow Bytes/s", "Flow Packets/s",
    "Flow IAT Mean", "Flow IAT Std", "Flow IAT Max", "Flow IAT Min",
    "Fwd IAT Total", "Fwd IAT Mean", "Bwd IAT Total", "Bwd IAT Mean",
    "Fwd Header Length", "Bwd Header Length",
    "Fwd Packets/s", "Bwd Packets/s",
]


# ─── FUNCTIONS ────────────────────────────────────────────────────────────────

def load_and_clean(path: str) -> pd.DataFrame:
    """Load CSV, drop nulls/infs, map labels."""
    print(f"[INFO] Loading dataset from: {path}")
    df = pd.read_csv(path, low_memory=False)

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    print(f"[INFO] Raw shape: {df.shape}")

    # Drop missing / infinite values
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)
    print(f"[INFO] After cleaning: {df.shape}")

    # Map labels to simplified categories
    label_col = [c for c in df.columns if "label" in c.lower()][0]
    df[label_col] = df[label_col].apply(
        lambda x: next(
            (v for k, v in ATTACK_LABELS.items() if k.lower() in str(x).lower()),
            "Other"
        )
    )
    return df


def preprocess(df: pd.DataFrame):
    """
    Scale features, encode labels, split data.
    Returns X_train, X_test, y_train, y_test and saves scaler/encoder.
    """
    label_col = [c for c in df.columns if "label" in c.lower()][0]

    # Keep only selected features that exist in the dataframe
    available = df.columns.tolist()
    features = [f for f in SELECTED_FEATURES if f in available]

    if not features:
        # Fallback: use all numeric columns except label
        features = df.select_dtypes(include=[np.number]).columns.tolist()
        features = [f for f in features if f != label_col]

    X = df[features].values
    y = df[label_col].values

    # Encode labels
    le = LabelEncoder()
    y_enc = le.fit_transform(y)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    # Save scaler and encoder
    os.makedirs("model", exist_ok=True)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(le, ENCODER_PATH)
    print(f"[INFO] Scaler saved  → {SCALER_PATH}")
    print(f"[INFO] Encoder saved → {ENCODER_PATH}")
    print(f"[INFO] Classes       : {list(le.classes_)}")
    print(f"[INFO] Train size: {X_train.shape} | Test size: {X_test.shape}")

    return X_train, X_test, y_train, y_test, le, features


def prepare_single_record(record: dict) -> tuple:
    """
    Preprocess a single incoming traffic record (dict) for prediction.
    Returns (scaled_array, label_encoder).
    """
    scaler: StandardScaler = joblib.load(SCALER_PATH)
    le: LabelEncoder       = joblib.load(ENCODER_PATH)

    vec = np.array(list(record.values()), dtype=float).reshape(1, -1)

    expected = scaler.n_features_in_
    if vec.shape[1] < expected:
        vec = np.pad(vec, ((0, 0), (0, expected - vec.shape[1])))
    elif vec.shape[1] > expected:
        vec = vec[:, :expected]

    return scaler.transform(vec), le


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("archive", exist_ok=True)

    if not os.path.exists(DATASET_PATH):
        print(f"[WARN] Dataset not found at '{DATASET_PATH}'.")
        print("[INFO] Generating synthetic dataset for demo …")

        np.random.seed(42)
        n = 5000
        labels = np.random.choice(
            ["Normal Traffic", "DDoS", "Port Scan", "Brute Force", "Botnet"],
            size=n, p=[0.6, 0.15, 0.1, 0.1, 0.05],
        )
        data = {f"feature_{i}": np.random.randn(n) for i in range(26)}
        data["Label"] = labels
        df_demo = pd.DataFrame(data)
        df_demo.to_csv(DATASET_PATH, index=False)
        print(f"[INFO] Synthetic dataset saved → {DATASET_PATH}")
        df = df_demo
    else:
        df = load_and_clean(DATASET_PATH)

    df.to_csv(CLEAN_CSV, index=False)
    print(f"[INFO] Clean dataset saved → {CLEAN_CSV}")

    X_train, X_test, y_train, y_test, le, feat_names = preprocess(df)
    print("[DONE] Preprocessing complete.")