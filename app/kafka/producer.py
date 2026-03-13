"""
UPI Secure Pay AI - Kafka Producer
"""

import json
import asyncio
from typing import Optional
from datetime import datetime

# Make aiokafka optional - will work without it for development
try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaProducer = None
    AIOKafkaConsumer = None

from loguru import logger

from app.config import get_settings

settings = get_settings()

# Kafka producer instance
producer: Optional[AIOKafkaProducer] = None


# ==================== Topic Names ====================

class Topics:
    """Kafka topic names"""
    RAW_TRANSACTIONS = settings.kafka_topic_raw_transactions
    SCORED_TRANSACTIONS = settings.kafka_topic_scored
    ALERTS = settings.kafka_topic_alerts
    AUDIT = settings.kafka_topic_audit


# ==================== Producer Functions ====================

async def get_producer() -> Optional[AIOKafkaProducer]:
    """Get Kafka producer instance"""
    global producer
    
    if not KAFKA_AVAILABLE:
        return None
        
    if producer is None:
        producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
        )
        await producer.start()
    return producer


async def close_producer():
    """Close Kafka producer"""
    global producer
    if producer and KAFKA_AVAILABLE:
        await producer.stop()
        producer = None


async def publish_transaction(transaction: dict) -> bool:
    """Publish raw transaction to Kafka"""
    try:
        if not KAFKA_AVAILABLE:
            logger.info(f"Kafka not available, skipping publish: {transaction.get('transaction_id')}")
            return True
            
        p = await get_producer()
        if p is None:
            return True
        
        # Add timestamp
        transaction['published_at'] = datetime.utcnow().isoformat()
        
        await p.send(
            Topics.RAW_TRANSACTIONS,
            key=transaction.get('transaction_id'),
            value=transaction
        )
        await p.flush()
        
        logger.info(f"Published transaction: {transaction.get('transaction_id')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish transaction: {e}")
        return False


async def publish_scored_transaction(transaction: dict) -> bool:
    """Publish scored transaction to Kafka"""
    try:
        if not KAFKA_AVAILABLE:
            return True
            
        p = await get_producer()
        if p is None:
            return True
            
        await p.send(
            Topics.SCORED_TRANSACTIONS,
            key=transaction.get('transaction_id'),
            value=transaction
        )
        await p.flush()
        
        logger.info(f"Published scored transaction: {transaction.get('transaction_id')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish scored transaction: {e}")
        return False


async def publish_alert(alert: dict) -> bool:
    """Publish fraud alert to Kafka"""
    try:
        if not KAFKA_AVAILABLE:
            return True
            
        p = await get_producer()
        if p is None:
            return True
            
        await p.send(
            Topics.ALERTS,
            key=alert.get('transaction_id'),
            value=alert
        )
        await p.flush()
        
        logger.info(f"Published alert: {alert.get('alert_type')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to publish alert: {e}")
        return False


# ==================== Producer Wrapper Class ====================

class KafkaProducerService:
    """Kafka producer service wrapper"""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
    
    async def start(self):
        """Start the producer"""
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
        )
        await self.producer.start()
        logger.info("Kafka producer started")
    
    async def stop(self):
        """Stop the producer"""
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped")
    
    async def send(self, topic: str, key: str, value: dict):
        """Send message to topic"""
        if not self.producer:
            raise RuntimeError("Producer not started")
        
        await self.producer.send(topic, key=key, value=value)
        await self.producer.flush()
    
    async def send_batch(self, topic: str, messages: list):
        """Send batch of messages"""
        if not self.producer:
            raise RuntimeError("Producer not started")
        
        for msg in messages:
            await self.producer.send(topic, key=msg.get('key'), value=msg.get('value'))
        
        await self.producer.flush()
