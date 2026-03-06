"""
UPI Secure Pay AI - Configuration Module
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = "UPI Secure Pay AI"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/upi_secure_pay"
    database_url_sync: str = "postgresql://postgres:postgres@localhost:5432/upi_secure_pay"
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_raw_transactions: str = "upi.transactions.raw"
    kafka_topic_scored: str = "upi.transactions.scored"
    kafka_topic_alerts: str = "upi.alerts"
    kafka_topic_audit: str = "upi.audit"
    kafka_consumer_group: str = "fraud-processor"
    
    # JWT
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    
    # ML Models
    lightgbm_model_path: str = "models/lightgbm/fraud_model.txt"
    transformer_model_path: str = "models/transformer/fraud_transformer"
    ensemble_weight_lightgbm: float = 0.5
    ensemble_weight_transformer: float = 0.5
    
    # Fraud Detection
    fraud_threshold_block: int = 85
    fraud_threshold_review: int = 60
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
