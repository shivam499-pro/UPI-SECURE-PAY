"""
UPI Secure Pay AI - Kafka Consumer
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger

# Make aiokafka optional
try:
    from aiokafka import AIOKafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaConsumer = None

from app.config import get_settings
from app.ml.orchestrator import get_fraud_cascade_engine
from app.database import Transaction, get_db, AsyncSession
from sqlalchemy import insert

settings = get_settings()

# Consumer instance
consumer: Optional[AIOKafkaConsumer] = None

# Consumer stats
consumer_stats = {
    "running": False,
    "messages_processed": 0,
    "last_message_at": None,
    "errors_count": 0,
    "started_at": None,
}


async def get_consumer() -> Optional[AIOKafkaConsumer]:
    """Get or create Kafka consumer instance"""
    global consumer
    
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka not available, consumer will not start")
        return None
    
    if consumer is None:
        consumer = AIOKafkaConsumer(
            settings.kafka_topic_raw_transactions,  # Subscribe to raw transactions
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            auto_offset_reset='latest',  # Start from latest messages
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
        )
    
    return consumer


async def start_consumer():
    """Start the Kafka consumer"""
    global consumer, consumer_stats
    
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka not available, skipping consumer start")
        return False
    
    try:
        consumer = await get_consumer()
        if consumer is None:
            return False
        
        await consumer.start()
        consumer_stats["running"] = True
        consumer_stats["started_at"] = datetime.utcnow().isoformat()
        logger.info(f"Kafka consumer started, subscribed to: {settings.kafka_topic_raw_transactions}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to start Kafka consumer: {e}")
        consumer_stats["running"] = False
        return False


async def stop_consumer():
    """Stop the Kafka consumer gracefully"""
    global consumer, consumer_stats
    
    if consumer and KAFKA_AVAILABLE:
        try:
            await consumer.stop()
            logger.info("Kafka consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")
    
    consumer = None
    consumer_stats["running"] = False


async def process_message(transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single transaction through FraudCascadeEngine.
    
    Args:
        transaction_data: Transaction dictionary from Kafka
        
    Returns:
        Processing result with fraud decision
    """
    try:
        # Get the cascade engine (singleton, initialized at startup)
        cascade_engine = await get_fraud_cascade_engine()
        
        # Run fraud detection
        result = await cascade_engine.predict(transaction_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing transaction: {e}")
        # Return a safe default result
        return {
            "final_verdict": "verify",
            "cascade_stage": "PROCESSING_ERROR",
            "risk_score": 50.0,
            "model_scores": {},
            "safety_rules_triggered": [],
            "levels_used": [],
            "latency_ms": 0,
            "decision_reason": f"Processing error: {str(e)}"
        }


async def save_transaction_to_db(transaction_data: Dict[str, Any], result: Dict[str, Any]):
    """Save transaction and result to database"""
    try:
        async for db in get_db():
            db_transaction = Transaction(
                transaction_id=transaction_data.get('transaction_id', f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
                sender_id=transaction_data.get('sender_id', ''),
                sender_vpa=transaction_data.get('sender_vpa', ''),
                receiver_id=transaction_data.get('receiver_id', ''),
                receiver_vpa=transaction_data.get('receiver_vpa', ''),
                amount=transaction_data.get('amount', 0),
                timestamp=datetime.utcnow(),
                status='completed',
                fraud_score=result.get('risk_score', 0) / 100,  # Convert to 0-1
                decision=result.get('final_verdict', 'verify'),
                device_id=transaction_data.get('sender_device_id', ''),
                ip_address=transaction_data.get('ip_address', ''),
                cascade_stage=result.get('cascade_stage'),
                safety_rules_triggered=json.dumps(result.get('safety_rules_triggered', [])),
                levels_used=json.dumps(result.get('levels_used', [])),
                processing_time_ms=result.get('latency_ms', 0)
            )
            db.add(db_transaction)
            await db.commit()
            logger.info(f"Saved transaction {db_transaction.transaction_id} to database")
            break
            
    except Exception as e:
        logger.error(f"Failed to save transaction to database: {e}")


async def consume_messages():
    """
    Main consumer loop - processes messages from Kafka.
    This runs as a background task.
    """
    global consumer_stats
    
    if not KAFKA_AVAILABLE:
        logger.warning("Kafka not available, consumer loop will not run")
        return
    
    max_retries = 5
    retry_delay = 5  # seconds
    
    while True:
        try:
            consumer = await get_consumer()
            if consumer is None:
                logger.warning("Consumer not available, retrying...")
                await asyncio.sleep(retry_delay)
                continue
            
            # Check if consumer is running
            if not consumer_stats["running"]:
                await start_consumer()
            
            # Consume messages
            async for msg in consumer:
                try:
                    transaction_data = msg.value
                    transaction_id = transaction_data.get('transaction_id', 'unknown')
                    
                    logger.info(f"Received transaction: {transaction_id}")
                    
                    # Process through FraudCascadeEngine
                    result = await process_message(transaction_data)
                    
                    # Save to database
                    await save_transaction_to_db(transaction_data, result)
                    
                    # Update stats
                    consumer_stats["messages_processed"] += 1
                    consumer_stats["last_message_at"] = datetime.utcnow().isoformat()
                    
                    logger.info(
                        f"Processed {transaction_id}: "
                        f"decision={result.get('final_verdict')}, "
                        f"score={result.get('risk_score')}, "
                        f"stage={result.get('cascade_stage')}"
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    consumer_stats["errors_count"] += 1
                    # Continue to next message - don't crash
                    continue
                    
        except asyncio.CancelledError:
            logger.info("Consumer loop cancelled")
            break
        except Exception as e:
            logger.error(f"Consumer error: {e}")
            consumer_stats["errors_count"] += 1
            # Retry with backoff
            for i in range(max_retries):
                await asyncio.sleep(retry_delay * (i + 1))
                if consumer_stats["running"]:
                    break


def get_consumer_stats() -> Dict[str, Any]:
    """Get consumer statistics"""
    return {
        "running": consumer_stats["running"],
        "messages_processed": consumer_stats["messages_processed"],
        "last_message_at": consumer_stats["last_message_at"],
        "errors_count": consumer_stats["errors_count"],
        "started_at": consumer_stats.get("started_at"),
        "kafka_available": KAFKA_AVAILABLE,
        "topic": settings.kafka_topic_raw_transactions,
        "consumer_group": settings.kafka_consumer_group,
    }


async def reset_consumer_stats():
    """Reset consumer statistics"""
    global consumer_stats
    consumer_stats = {
        "running": False,
        "messages_processed": 0,
        "last_message_at": None,
        "errors_count": 0,
        "started_at": None,
    }
