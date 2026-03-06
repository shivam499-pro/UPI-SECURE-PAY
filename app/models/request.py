"""
UPI Secure Pay AI - Request Models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class TransactionRequest(BaseModel):
    """Request model for transaction data"""
    
    sender_id: str = Field(..., description="Sender user ID", min_length=1, max_length=50)
    sender_vpa: str = Field(..., description="Sender's Virtual Payment Address")
    sender_device_id: str = Field(..., description="Sender's device ID")
    receiver_id: str = Field(..., description="Receiver user ID", min_length=1, max_length=50)
    receiver_vpa: str = Field(..., description="Receiver's Virtual Payment Address")
    amount: float = Field(..., description="Transaction amount in INR", gt=0)
    timestamp: str = Field(..., description="Transaction timestamp in ISO format")
    transaction_type: str = Field(..., description="Transaction type: P2P or P2M")
    merchant_category: Optional[str] = Field(None, description="Merchant category code")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Validate timestamp format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('Invalid timestamp format. Use ISO format.')
        return v
    
    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        """Validate transaction type"""
        valid_types = ['P2P', 'P2M', 'P2A', 'B2P', 'B2M']
        if v.upper() not in valid_types:
            raise ValueError(f'Transaction type must be one of: {valid_types}')
        return v.upper()


class FraudCheckRequest(BaseModel):
    """Request model for fraud check"""
    
    transaction: TransactionRequest
    sender_history_days: int = Field(30, description="Number of days of history to consider", ge=1, le=90)
    include_device_analysis: bool = Field(True, description="Include device analysis")
    include_merchant_analysis: bool = Field(True, description="Include merchant analysis")


class FeedbackRequest(BaseModel):
    """Request model for feedback submission"""
    
    transaction_id: str = Field(..., description="Transaction ID")
    is_correct: bool = Field(..., description="Was the decision correct?")
    actual_label: Optional[str] = Field(None, description="Actual fraud label if known")
    comments: Optional[str] = Field(None, description="Additional comments")


class BatchFraudCheckRequest(BaseModel):
    """Request model for batch fraud check"""
    
    transactions: List[TransactionRequest] = Field(..., description="List of transactions", min_items=1, max_items=1000)


class HealthCheckRequest(BaseModel):
    """Request model for health check"""
    
    include_models: bool = Field(False, description="Include model status in response")
    include_database: bool = Field(False, description="Include database status in response")
    include_cache: bool = Field(False, description="Include cache status in response")
    include_kafka: bool = Field(False, description="Include Kafka status in response")
