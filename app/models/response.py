"""
UPI Secure Pay AI - Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class FraudScoreModel(BaseModel):
    """Individual model fraud score"""
    
    model_name: str = Field(..., description="Name of the model")
    score: float = Field(..., description="Fraud score from model (0-1)", ge=0, le=1)
    weight: float = Field(..., description="Weight of this model in ensemble", ge=0, le=1)
    features_used: Optional[List[str]] = Field(None, description="Features used by this model")


class FraudCheckResponse(BaseModel):
    """Response model for fraud check"""
    
    transaction_id: str = Field(..., description="Transaction ID")
    status: str = Field(..., description="Overall status: approved, blocked, or review")
    risk_score: float = Field(..., description="Final risk score (0-100)", ge=0, le=100)
    decision: str = Field(..., description="Decision: proceed, block, or verify")
    reasons: List[str] = Field(..., description="List of reasons for the decision")
    model_scores: List[FraudScoreModel] = Field(..., description="Individual model scores")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: str = Field(..., description="Response timestamp in ISO format")
    
    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN123456789",
                "status": "blocked",
                "risk_score": 92.5,
                "decision": "block",
                "reasons": [
                    "High amount transaction from new device",
                    "Unusual transaction time (3 AM)",
                    "Receiver has high fraud reports"
                ],
                "model_scores": [
                    {
                        "model_name": "lightgbm",
                        "score": 0.89,
                        "weight": 0.5,
                        "features_used": ["amount", "hour", "device_new"]
                    },
                    {
                        "model_name": "transformer",
                        "score": 0.94,
                        "weight": 0.5,
                        "features_used": ["amount", "hour", "device_new", "merchant_category"]
                    }
                ],
                "processing_time_ms": 45.2,
                "timestamp": "2026-03-05T18:30:00Z"
            }
        }


class BatchFraudCheckResponse(BaseModel):
    """Response model for batch fraud check"""
    
    total_transactions: int = Field(..., description="Total number of transactions")
    processed_transactions: int = Field(..., description="Number of transactions processed")
    failed_transactions: int = Field(..., description="Number of transactions that failed")
    results: List[FraudCheckResponse] = Field(..., description="Individual transaction results")
    total_processing_time_ms: float = Field(..., description="Total processing time in milliseconds")


class TransactionResponse(BaseModel):
    """Response model for transaction details"""
    
    transaction_id: str
    sender_id: str
    sender_vpa: str
    receiver_id: str
    receiver_vpa: str
    amount: float
    timestamp: str
    status: str
    fraud_score: Optional[float] = None
    decision: Optional[str] = None


class AlertResponse(BaseModel):
    """Response model for alerts"""
    
    alert_id: int
    transaction_id: str
    alert_type: str
    severity: str
    created_at: str
    resolved: bool
    resolution_notes: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check"""
    
    status: str = Field(..., description="Overall service status")
    version: str = Field(..., description="Application version")
    timestamp: str = Field(..., description="Health check timestamp")
    uptime_seconds: float = Field(..., description="Service uptime in seconds")
    models_loaded: Optional[bool] = Field(None, description="Whether ML models are loaded")
    database_connected: Optional[bool] = Field(None, description="Database connection status")
    cache_connected: Optional[bool] = Field(None, description="Cache connection status")
    kafka_connected: Optional[bool] = Field(None, description="Kafka connection status")


class AnalyticsResponse(BaseModel):
    """Response model for analytics data"""
    
    period: str = Field(..., description="Analytics period")
    total_transactions: int = Field(..., description="Total transactions in period")
    total_amount: float = Field(..., description="Total transaction amount")
    fraud_transactions: int = Field(..., description="Number of fraud transactions")
    fraud_rate: float = Field(..., description="Fraud rate percentage")
    blocked_transactions: int = Field(..., description="Number of blocked transactions")
    review_transactions: int = Field(..., description="Number of transactions sent for review")
    avg_risk_score: float = Field(..., description="Average risk score")
    top_fraud_types: List[Dict[str, Any]] = Field(..., description="Top fraud types")
    hourly_distribution: List[Dict[str, int]] = Field(..., description="Hourly transaction distribution")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    
    status: str = Field(..., description="Feedback submission status")
    message: str = Field(..., description="Feedback message")
    feedback_id: Optional[int] = Field(None, description="Feedback ID if stored")


class ErrorResponse(BaseModel):
    """Response model for errors"""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: str = Field(..., description="Error timestamp")


class ModelStatusResponse(BaseModel):
    """Response model for model status"""
    
    lightgbm_loaded: bool = Field(..., description="LightGBM model loaded")
    transformer_loaded: bool = Field(..., description="Transformer model loaded")
    models_path: Dict[str, str] = Field(..., description="Paths to model files")
    ensemble_weights: Dict[str, float] = Field(..., description="Ensemble weights")
    last_loaded: Optional[str] = Field(None, description="Last model loading timestamp")
