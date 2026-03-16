"""
train_model.py
--------------
Step 3: AI Model Training
- Runs preprocessing
- Trains RandomForestClassifier on CICIDS2017 data
- Evaluates model accuracy
- Saves trained model as model/cyber_model.pkl
- Saves real accuracy to model/model_meta.json
"""

import os
import json
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

from preprocess import preprocess, load_and_clean, DATASET_PATH, CLEAN_CSV

# ─── CONFIG ───────────────────────────────────────────────────────────────────
MODEL_PATH   = "model/cyber_model.pkl"
META_PATH    = "model/model_meta.json"
N_ESTIMATORS = 100
RANDOM_STATE = 42


# ─── TRAIN ────────────────────────────────────────────────────────────────────
def train():
    import pandas as pd

    # ── Load dataset ──────────────────────────────────────────────────────────
    if not os.path.exists(DATASET_PATH):
        print("[WARN] Raw dataset missing — generating demo data.")
        os.system("python model/preprocess.py")

    if os.path.exists(CLEAN_CSV):
        print(f"[INFO] Loading clean dataset from {CLEAN_CSV}")
        df = pd.read_csv(CLEAN_CSV)
    else:
        df = load_and_clean(DATASET_PATH)

    # ── Preprocess ────────────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test, le, features = preprocess(df)

    # ── Train ─────────────────────────────────────────────────────────────────
    print(f"\n[INFO] Training RandomForestClassifier with {N_ESTIMATORS} trees ...")
    clf = RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=20,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)
    print("[INFO] Training complete.")

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred = clf.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)

    print(f"\n{'='*55}")
    print(f"  Accuracy : {acc * 100:.2f}%")
    print(f"{'='*55}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0))

    # ── Save model ────────────────────────────────────────────────────────────
    os.makedirs("model", exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    print(f"[INFO] Model saved → {MODEL_PATH}")

    # ── Save real accuracy to JSON (read by app.py at runtime) ────────────────
    with open(META_PATH, "w") as f:
        json.dump({"accuracy": round(float(acc), 4)}, f)
    print(f"[INFO] Model meta saved → {META_PATH}  (accuracy={round(float(acc)*100,2)}%)")

    return clf, le


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    train()
    print("[DONE] Model training complete.")