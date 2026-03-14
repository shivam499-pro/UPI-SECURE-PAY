"""
UPI Secure Pay AI - Database Configuration
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, Index
from datetime import datetime
from typing import AsyncGenerator

from app.config import get_settings

settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


# ==================== Database Models ====================

class User(Base):
    """User table"""
    __tablename__ = "users"
    
    user_id = Column(String(50), primary_key=True)
    vpa = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    kyc_verified = Column(Boolean, default=False)
    risk_level = Column(String(20), default="normal")  # normal, elevated, high
    last_activity = Column(DateTime)
    
    __table_args__ = (
        Index("idx_user_risk", "risk_level"),
    )


class Device(Base):
    """Device table"""
    __tablename__ = "devices"
    
    device_id = Column(String(100), primary_key=True)
    user_id = Column(String(50), nullable=False, index=True)
    device_type = Column(String(50))
    os_version = Column(String(20))
    is_rooted = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_device_user", "user_id"),
    )


class Merchant(Base):
    """Merchant table"""
    __tablename__ = "merchants"
    
    merchant_id = Column(String(50), primary_key=True)
    vpa = Column(String(100), unique=True, index=True)
    merchant_name = Column(String(200))
    category = Column(String(50))
    risk_score = Column(Float, default=0.0)
    fraud_reports = Column(Integer, default=0)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_merchant_risk", "risk_score"),
    )


class Transaction(Base):
    """Transaction table"""
    __tablename__ = "transactions"
    
    transaction_id = Column(String(50), primary_key=True)
    sender_id = Column(String(50), nullable=False, index=True)
    sender_vpa = Column(String(100))
    receiver_id = Column(String(50), nullable=False, index=True)
    receiver_vpa = Column(String(100))
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(20))  # pending, completed, failed
    fraud_score = Column(Float)
    decision = Column(String(20))  # approved, blocked, review
    device_id = Column(String(100))
    ip_address = Column(String(45))
    
    # New fields for FraudCascadeEngine tracking
    cascade_stage = Column(String(50), nullable=True)  # LEVEL 1, LEVEL 2, LEVEL 3, etc.
    safety_rules_triggered = Column(Text, nullable=True)  # JSON string of triggered rules
    levels_used = Column(Text, nullable=True)  # JSON string of ML levels used
    processing_time_ms = Column(Float, nullable=True)
    
    __table_args__ = (
        Index("idx_txn_sender_time", "sender_id", "timestamp"),
        Index("idx_txn_receiver_time", "receiver_id", "timestamp"),
        Index("idx_txn_timestamp", "timestamp"),
        Index("idx_txn_decision", "decision"),
        Index("idx_txn_fraud_score", "fraud_score"),
    )


class Alert(Base):
    """Alerts table"""
    __tablename__ = "alerts"
    
    alert_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(50))
    severity = Column(String(20))  # low, medium, high, critical
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(Text)


class TransactionMetrics(Base):
    """Time-series metrics table"""
    __tablename__ = "transaction_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    transaction_count = Column(Integer, default=0)
    total_amount = Column(Float, default=0.0)
    fraud_count = Column(Integer, default=0)
    avg_fraud_score = Column(Float, default=0.0)
    
    __table_args__ = (
        Index("idx_metrics_timestamp", "timestamp"),
    )


# ==================== Database Functions ====================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await async_engine.dispose()
