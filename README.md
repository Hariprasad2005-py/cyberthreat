# CyberThreat Detection System
## Dataset
Download CICIDS2017 from: https://www.kaggle.com/datasets/cicdataset/cicids2017
Place CSV files in archive/ folder and rename to dataset.csv
# 🛡️ CyberThreat AI — Intelligent Threat Detection & Network Anomaly Intelligence System

> **Hackathon Problem:** PS-AIML-02 — AI-Driven Cyber Threat Detection and Network Anomaly Intelligence System

**Live Dashboard:** https://hariprasad2005-py.github.io/cyberthreat/
**Live API:** https://cyberthreat-api.onrender.com

---

## 📌 Problem Statement

Organizations face increasingly sophisticated cyber threats that traditional rule-based systems fail to detect in time. This project builds an **AI-powered cybersecurity platform** capable of:

- Analyzing network traffic logs and system activity patterns
- Detecting and predicting potential threats in real-time
- Identifying behavioral anomalies using unsupervised learning
- Providing a security analytics dashboard for proactive monitoring and response

---

## 🏗️ System Architecture

```
CICIDS2017 Dataset
       │
       ▼
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  preprocess.py  │────▶│   train_model.py      │────▶│  cyber_model.pkl    │
│  Data cleaning  │     │  Random Forest (100)  │     │  scaler.pkl         │
│  Feature eng.   │     │  Isolation Forest     │     │  label_encoder.pkl  │
└─────────────────┘     └──────────────────────┘     └─────────────────────┘
                                                                │
                                                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         app.py  (Flask REST API)                         │
│  POST /predict  │  GET /history  │  GET /stats  │  GET /model_info       │
│  Auto-Simulator replays CICIDS2017 rows every 2 seconds                  │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      dashboard.py  (Streamlit)                           │
│  6 KPI Cards │ Threat Gauge │ Global Map │ Timeline │ Prediction Card    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 AI Models

### 1. Random Forest Classifier
- **Purpose:** Multi-class attack type classification
- **Dataset:** CICIDS2017 (Canadian Institute for Cybersecurity)
- **Trees:** 100 estimators, max depth 20
- **Classes:** DDoS, Botnet, Port Scan, Brute Force, Web Attack, DoS, Infiltration, Heartbleed, Normal Traffic
- **Accuracy:** 97%+
- **Features:** 26 network traffic features (destination port, flow duration, packet lengths, inter-arrival times, header lengths, etc.)

### 2. Isolation Forest (Anomaly Detection)
- **Purpose:** Unsupervised anomaly detection for zero-day / unknown threats
- **Contamination:** 5%
- **Estimators:** 100
- **Runs parallel** to the classifier on every prediction

### 3. Trend-Weighted Threat Prediction
- **Purpose:** Predict the next likely attack type
- **Method:** Frequency analysis on last 10 events with recency weighting
- **Output:** Attack type + confidence percentage

---

## 📁 Project Structure

```
cyberthreat/
│
├── backend/
│   └── app.py               # Flask REST API + auto-simulator + keep-alive
│
├── dashboard/
│   └── dashboard.py         # Streamlit dashboard with Three.js intro
│
├── model/
│   ├── preprocess.py        # Data cleaning, feature engineering, encoding
│   ├── train_model.py       # Model training + saves model_meta.json
│   ├── cyber_model.pkl      # Trained Random Forest model
│   ├── scaler.pkl           # StandardScaler
│   ├── label_encoder.pkl    # LabelEncoder for attack classes
│   └── model_meta.json      # Real accuracy saved at training time
│
├── simulator/
│   └── send_data.py         # Manual traffic simulator (optional)
│
├── archive/
│   ├── dataset.csv          # Raw CICIDS2017 CSV (not committed)
│   └── clean_dataset.csv    # Preprocessed dataset
│
├── blocked_ips.json         # Persisted blocked IPs (auto-created)
└── requirements.txt
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.9+
- pip

### 1. Clone the repository
```bash
git clone https://github.com/your-username/cyberthreat.git
cd cyberthreat
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download Dataset
Download CICIDS2017 from [Kaggle](https://www.kaggle.com/datasets/cicdataset/cicids2017) and place the CSV files in `archive/`. Rename or merge into `archive/dataset.csv`.

### 4. Preprocess & Train
```bash
cd model
python preprocess.py    # Cleans data, saves clean_dataset.csv + scaler/encoder
python train_model.py   # Trains Random Forest, saves model + model_meta.json
```

### 5. Run the API
```bash
cd backend
python app.py
# API runs on http://localhost:5000
```

### 6. Run the Dashboard
```bash
cd dashboard
streamlit run dashboard.py
# Dashboard opens at http://localhost:8501
```

---

## 🌐 API Reference

Base URL: `https://cyberthreat-api.onrender.com`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| POST | `/predict` | Classify a network traffic record |
| GET | `/history?limit=100` | Last N predictions |
| GET | `/stats` | Aggregated threat statistics |
| GET | `/model_info` | Model details + live confidence |
| GET | `/blocked_ips` | List of blocked IPs |
| POST | `/block_ip` | Block an IP address |
| POST | `/unblock_ip` | Unblock an IP address |

### Sample Predict Request
```bash
curl -X POST https://cyberthreat-api.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Destination Port": 80,
    "Flow Duration": 1234567,
    "Total Fwd Packets": 5,
    "Total Backward Packets": 3,
    "source_ip": "203.0.1.1"
  }'
```

### Sample Response
```json
{
  "attack_type": "DDoS",
  "risk_score": 0.9142,
  "confidence": 0.9871,
  "source_ip": "203.0.1.1",
  "timestamp": "2026-03-17T14:23:11.456789",
  "threat_level": "HIGH",
  "is_anomaly": true
}
```

---

## 📊 Dashboard Features

| Feature | Description |
|---------|-------------|
| **Three.js Intro** | 5-second live network topology visualization on load |
| **6 KPI Cards** | Total Requests, High Risk, Avg Risk Score, Anomalies, Live Confidence, Attacks/Min |
| **Threat Severity Gauge** | Speedometer showing CRITICAL / HIGH / MEDIUM / LOW |
| **Threat Intelligence Summary** | Auto-generated SOC-style report with dominant threat, anomaly rate, latest IP |
| **AI Prediction Card** | Animated next-threat prediction with confidence bar |
| **Global Threat Map** | World map with color-coded attack origin bubbles |
| **Attack Distribution** | Live donut chart with percentage breakdown |
| **Risk Score Timeline** | Line chart with HIGH/MED/LOW shaded zones |
| **Live Threat Alerts** | Real-time color-coded alert feed |
| **Top Suspicious IPs** | IP table sorted by attack count |
| **Attack Volume Bar Chart** | Horizontal bar chart by attack type |
| **Network Traffic Volume** | Area chart of requests per 10-second bucket |
| **Export** | Download CSV (raw data) or TXT summary report |
| **Sound Alerts** | Audio ping on HIGH threat detection |
| **Auto Refresh** | Dashboard refreshes every 5 seconds |

---

## 🔢 Features Used (CICIDS2017)

| # | Feature | Description |
|---|---------|-------------|
| 1 | Destination Port | Target port number |
| 2 | Flow Duration | Total flow duration in microseconds |
| 3 | Total Fwd Packets | Packets sent in forward direction |
| 4 | Total Backward Packets | Packets sent in backward direction |
| 5 | Total Length of Fwd Packets | Total size of forward packets |
| 6 | Fwd/Bwd Packet Length (Max/Min/Mean) | Packet size statistics |
| 7 | Flow Bytes/s | Bytes transferred per second |
| 8 | Flow Packets/s | Packets transferred per second |
| 9 | Flow IAT (Mean/Std/Max/Min) | Inter-arrival time statistics |
| 10 | Fwd/Bwd IAT Total/Mean | Direction-specific inter-arrival times |
| 11 | Fwd/Bwd Header Length | Header size statistics |
| 12 | Fwd/Bwd Packets/s | Directional packet rates |

---

## 🛡️ Attack Classes & Risk Scores

| Attack Type | Risk Score | Description |
|-------------|-----------|-------------|
| Infiltration | 0.95 | Network infiltration attempts |
| DDoS | 0.92 | Distributed Denial of Service |
| Heartbleed | 0.90 | OpenSSL Heartbleed exploit |
| DoS | 0.88 | Denial of Service attacks |
| Botnet | 0.85 | Botnet C&C communication |
| Brute Force | 0.75 | FTP/SSH brute force login |
| Web Attack | 0.70 | SQL injection, XSS, etc. |
| Port Scan | 0.60 | Network reconnaissance |
| Normal Traffic | 0.02 | Benign network activity |

---

## ☁️ Deployment

### Backend (Render)
- Platform: [Render.com](https://render.com) (Free tier)
- Service type: Web Service
- Build command: `pip install -r requirements.txt`
- Start command: `python backend/app.py`
- Keep-alive: Built-in thread pings `/health` every 10 minutes

### Dashboard (Render / Streamlit Cloud)
- Platform: Render or [Streamlit Community Cloud](https://streamlit.io/cloud)
- Start command: `streamlit run dashboard/dashboard.py --server.port $PORT --server.address 0.0.0.0`

---

## 📦 Requirements

```
pandas
numpy
scikit-learn
flask
flask-cors
streamlit
plotly
requests
joblib
```

---

## 📈 Model Performance

| Metric | Value |
|--------|-------|
| Algorithm | Random Forest + Isolation Forest |
| Dataset | CICIDS2017 |
| Train/Test Split | 80% / 20% |
| Accuracy | 97%+ |
| Features | 26 network traffic features |
| Trees | 100 estimators |
| Anomaly Detection | Isolation Forest (5% contamination) |
| Inference Speed | < 5ms per prediction |

---

## 👨‍💻 Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Model | scikit-learn (Random Forest, Isolation Forest) |
| API Backend | Flask + Flask-CORS |
| Dashboard | Streamlit |
| Charts | Plotly |
| 3D Visualization | Three.js (r128) |
| Data Processing | pandas, numpy |
| Model Persistence | joblib |
| Deployment | Render.com |

---

## 🎯 Problem Statement Mapping

| Requirement | Implementation |
|-------------|---------------|
| AI-powered platform | Random Forest (97% acc) + Isolation Forest |
| Analyze network traffic logs | 26 CICIDS2017 features per prediction |
| System activity pattern analysis | Auto-simulator replays real dataset rows |
| Behavioral anomaly identification | Isolation Forest, anomaly flag per event |
| Detect potential threats | 9 attack classes, real-time classification |
| Predict potential threats | Trend-weighted prediction with confidence % |
| Security analytics dashboard | Full Streamlit dashboard, 15+ visualizations |
| Proactive monitoring | 5s auto-refresh, sound alerts, live KPIs |
| Respond to emerging threats | Export reports, action log, keep-alive API |

---

## 📄 License

This project was built for the PS-AIML-02 Hackathon Challenge.

---

*Built with ❤️ for the hackathon — AI-Driven Cyber Threat Detection and Network Anomaly Intelligence System*
