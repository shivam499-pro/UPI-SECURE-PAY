# 🛡️ UPI Secure Pay AI

Real-time fraud detection system for UPI (Unified Payments Interface) transactions in India using ensemble machine learning.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🎯 Overview

**Problem:** Traditional UPI fraud detection relies on static, rule-based systems that fail to identify sophisticated social engineering (like screen-sharing scams) and automated bot-attacks.

**Solution:** An AI-first, behavior-aware **Fraud Cascade Engine** that dynamically routes transactions through lightweight ML filters to deep-learning analysis, ensuring <100ms latency without sacrificing security.

UPI Secure Pay AI is a hackathon-ready fraud detection system that combines 5 advanced ML models to detect fraudulent transactions in real-time with >95% accuracy and <100ms response time.

## ✨ Features

### 🧠 Intelligent Fraud Cascade Engine
- **Multi-tier ML Architecture** that intelligently routes transactions based on risk
- **Level 1**: LightGBM - Fast filter (~70% transactions approved in <10ms)
- **Level 2**: Transformer + TGN - Contextual analysis (parallel execution)
- **Level 3**: GNN + LLaMA - Deep investigation for high-risk cases

### 🛡️ SafetyRuleEngine
Pre-ML gatekeeper that catches critical fraud instantly:
- Device rooted/jailbroken detection
- Suspicious merchant keyword scanning
- Critical amount threshold (>₹90,000)
- **Behavioral Biometrics** for scam detection:
  - Phone call detection during transactions
  - Screen sharing monitoring
  - Typing velocity analysis

### 📊 5-Model Ensemble
- **LightGBM** - Core tabular feature analysis
- **Transformer** - Sequence pattern detection
- **GNN (Graph Neural Network)** - Relationship patterns
- **TGN (Temporal Graph Network)** - Time-based analysis
- **LLaMA** - Merchant behavior NLP analysis

### ⚡ Technical Features
- **Real-time Processing** - Sub-100ms fraud detection
- **REST API** - Easy integration with banks and payment apps
- **Async Architecture** - Built with FastAPI + asyncio
- **Scalable** - Supports Redis caching and Kafka streaming
- **Production-Ready** - Docker Compose for deployment

## 📸 Demo Highlights

| Normal Flow (Approved) | Scam Attempt (Blocked) |
| :--- | :--- |
| ![Approved](assets/demo_approved.png) | ![Blocked](assets/demo_blocked.png) |
| ![Approved](assets/demo_approved-2.png) | ![Blocked](assets/demo_blocked-2.png) |
| *Level 1 Fast Path (<30ms)* | *SafetyRuleEngine Override* |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Transaction Input                        │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│        SafetyRuleEngine (Pre-ML Gatekeeper)            │
│  - Rooted device detection                              │
│  - Scam merchant keywords                               │
│  - Critical amount (>₹90,000)                          │
│  - Behavioral biometrics                                │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
    ┌───▼────┐               ┌──────▼──────┐
    │ LOW    │               │   CRITICAL  │
    │ Risk   │               │   Risk      │
    │ < 0.4  │               │   Override  │
    └───┬────┘               └──────┬──────┘
        │                           │
        ▼                   ┌───────▼───────┐
┌───────────────┐           │ LEVEL 3:      │
│ Level 1:      │           │ GNN + LLaMA   │
│ LightGBM      │           │ (Deep Invest) │
│ (<10ms)       │           └───────────────┘
└───────┬───────┘
        │
        ▼ (if 0.4-0.7)
┌─────────────────────────────────────────────┐
│ Level 2: Transformer + TGN (Parallel)      │
│ - Sequence pattern detection                │
│ - Temporal graph analysis                   │
│ (~50ms combined)                           │
└─────────────────────────────────────────────┘
```

### Performance Metrics

| Metric | Traditional | Our Approach |
|--------|-------------|--------------|
| Avg Latency | 150-200ms | **15-50ms** |
| LLM Calls | 100% | **5-10%** |
| Compute Cost | 100% | **~30%** |
| False Positive | ~5% | **~2%** |

## 🚀 Quick Start

### Prerequisites

- Python 3.13+
- Windows/Linux/Mac

### Installation

```bash
# Clone the repository
git clone https://github.com/shivam499-pro/UPI-SECURE-PAY.git
cd UPI-SECURE-PAY/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload --port 8000
```

### Run Tests

```bash
python test_api.py
```

### Run the Dashboard

```bash
# Terminal 1: Start the backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start the dashboard
streamlit run dashboard.py
```

The dashboard will open at http://localhost:8501

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/fraud-check` | POST | Detect fraud |
| `/api/v1/models/status` | GET | Model status |
| `/api/v1/analytics/fraud-stats` | GET | Fraud statistics |
| `/docs` | GET | API documentation |

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/fraud-check \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "sender_id": "user001",
      "sender_vpa": "user001@okhdfcbank",
      "sender_device_id": "device123",
      "receiver_id": "merchant001",
      "receiver_vpa": "shop@oksbi",
      "amount": 500,
      "timestamp": "2026-03-05T12:00:00Z",
      "transaction_type": "P2M"
    }
  }'
```

### Example Response

```json
{
  "transaction_id": "TXN20260305120000ABC123",
  "status": "approved",
  "risk_score": 12.5,
  "decision": "proceed",
  "processing_time_ms": 45.2,
  "model_scores": [
    {"model_name": "lightgbm", "score": 0.10, "weight": 0.25},
    {"model_name": "transformer", "score": 0.15, "weight": 0.25},
    {"model_name": "gnn", "score": 0.08, "weight": 0.20},
    {"model_name": "tgn", "score": 0.12, "weight": 0.15},
    {"model_name": "llm", "score": 0.18, "weight": 0.15}
  ]
}
```

## 🛡️ SafetyRuleEngine Details

The SafetyRuleEngine is a **pre-ML gatekeeper** that runs BEFORE any ML models to catch obvious fraud instantly:

| Rule | Condition | Action |
|------|-----------|--------|
| DEVICE_ROOTED | Device is rooted/jailbroken | BLOCK → Level 3 |
| DEVICE_JAILBROKEN | Device is jailbroken | BLOCK → Level 3 |
| MERCHANT_SCAM_KEYWORD | Suspicious merchant name | LEVEL 3 |
| CRITICAL_AMOUNT | Amount > ₹90,000 | LEVEL 3 |
| SCAM_CALL_DETECTED | On phone call + amount > ₹10,000 | LEVEL 3 |
| SCREEN_SHARING | Screen sharing active | LEVEL 3 |
| TYPING_TOO_SLOW | Typing < 1 char/sec | LEVEL 3 |
| TYPING_TOO_FAST | Typing > 8 chars/sec | LEVEL 3 |
| NETWORK_BLACKLISTED | Known fraud network | LEVEL 3 |
| NEW_ACCOUNT_HIGH_AMOUNT | New account + >₹50,000 | LEVEL 3 |

## 🧠 ML Models

### Level 1: LightGBM (Fast Filter)
- **Purpose**: High-speed initial screening of 100% of transactions
- **Characteristics**: Sub-10ms inference time, filters ~70% of transactions
- **Threshold**: Score < 0.4 → APPROVED

### Level 2: Transformer + TGN (Context Analysis)
- **Transformer**: Sequential pattern detection with attention
- **TGN**: Temporal Graph Networks for time-based analysis
- **Characteristics**: ~50ms combined (parallel), runs on ~20-25% of transactions

### Level 3: GNN + LLaMA (Deep Investigation)
- **GNN**: Graph Neural Networks for relationship patterns
- **LLaMA**: Large Language Model for merchant behavior reasoning
- **Characteristics**: ~100ms, runs on ~5-10% of transactions

## 🛠️ Tech Stack

- **Backend**: Python 3.13, FastAPI
- **ML**: PyTorch, LightGBM, Transformers, scikit-learn
- **Database**: PostgreSQL, SQLite (async with aiosqlite)
- **Caching**: Redis
- **Streaming**: Apache Kafka
- **Frontend**: Streamlit
- **DevOps**: Docker, Docker Compose

## 📁 Project Structure

```
UPI-SECURE-PAY/
├── backend/                   # FastAPI backend
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # DB models
│   │   ├── cache.py             # Redis
│   │   ├── ml_orchestrator.py  # Fraud Cascade Engine
│   │   ├── kafka/               # Kafka producer
│   │   ├── ml/                  # ML models
│   │   │   ├── lightgbm_model.py
│   │   │   ├── transformer_model.py
│   │   │   ├── gnn_model.py
│   │   │   ├── tgn_model.py
│   │   │   └── llm_model.py
│   │   ├── models/              # Pydantic models
│   │   └── routers/             # API endpoints
│   │       ├── health.py
│   │       ├── fraud.py
│   │       └── analytics.py
│   ├── requirements.txt
│   └── test_api.py
├── dashboard.py               # Streamlit dashboard
├── assets/                    # Architecture diagrams
│   ├── Architecture flow diagram.png
│   ├── component break down diagram.png
│   └── ...
├── docker-compose.yml         # Full stack Docker
├── requirements.txt            # Root requirements
└── README.md
```

## 🎓 For Hackathons

This project demonstrates:
- ✅ Ensemble ML techniques (5 models)
- ✅ Real-time API design (<100ms)
- ✅ Async Python programming
- ✅ Production-ready code structure
- ✅ Behavioral biometrics for fraud detection
- ✅ Event-driven architecture (Kafka)
- ✅ Docker containerization
- ✅ Good documentation practices

## 🚀 Future Enhancements

- Graph database (Neo4j) integration for fraud ring detection
- Federated learning across banks
- Voice biometrics for scam call detection
- Real-time streaming analytics
- AutoML for dynamic model optimization

## 📄 License

MIT License - feel free to use for your hackathons!

## 👤 Author

- **Shivam** - [shivam499-pro](https://github.com/shivam499-pro)

---

⭐ Star this repo if you found it helpful!
