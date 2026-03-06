# UPI Secure Pay AI - Backend

## Project Structure

```
upi-secure-pay-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database connection
│   ├── cache.py                # Redis cache layer
│   ├── kafka/                  # Kafka producer/consumer
│   │   ├── __init__.py
│   │   ├── producer.py
│   │   └── consumer.py
│   ├── models/                 # Pydantic models
│   │   ├── __init__.py
│   │   ├── request.py         # Request models
│   │   └── response.py         # Response models
│   ├── schemas/                # Database schemas
│   │   ├── __init__.py
│   │   └── database.py         # SQLAlchemy models
│   ├── ml/                    # ML models
│   │   ├── __init__.py
│   │   ├── base.py            # Base model class
│   │   ├── lightgbm_model.py  # LightGBM implementation
│   │   └── transformer_model.py # Transformer implementation
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── fraud_service.py   # Main fraud detection service
│   │   └── analytics_service.py # Analytics service
│   ├── routers/               # API endpoints
│   │   ├── __init__.py
│   │   ├── health.py          # Health check endpoints
│   │   ├── fraud.py           # Fraud detection endpoints
│   │   └── analytics.py       # Analytics endpoints
│   └── utils/                 # Utilities
│       ├── __init__.py
│       └── helpers.py
├── models/                    # Trained ML models
│   ├── lightgbm/
│   │   └── fraud_model.txt
│   └── transformer/
│       └── fraud_transformer/
├── tests/                     # Unit tests
│   ├── __init__.py
│   ├── test_fraud.py
│   └── test_models.py
├── .env                      # Environment variables
├── .env.example
├── requirements.txt           # Python dependencies
├── docker-compose.yml         # Docker setup
├── Dockerfile               # Docker image
└── README.md               # Project documentation
