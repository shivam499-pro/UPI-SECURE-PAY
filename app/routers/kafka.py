"""
UPI Secure Pay AI - Kafka Router
"""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from loguru import logger

from app.kafka import get_consumer_stats, reset_consumer_stats

router = APIRouter()


@router.get("/kafka/status")
async def get_kafka_status():
    """
    Get Kafka consumer status and statistics.
    
    Returns:
        - consumer running status
        - messages processed count
        - last message timestamp
        - errors count
    """
    try:
        stats = get_consumer_stats()
        
        return {
            "consumer_running": stats["running"],
            "messages_processed": stats["messages_processed"],
            "last_message_at": stats["last_message_at"],
            "errors_count": stats["errors_count"],
            "started_at": stats.get("started_at"),
            "kafka_available": stats["kafka_available"],
            "topic": stats["topic"],
            "consumer_group": stats["consumer_group"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Get Kafka status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kafka/reset-stats")
async def reset_kafka_stats():
    """
    Reset Kafka consumer statistics.
    """
    try:
        await reset_consumer_stats()
        
        return {
            "status": "success",
            "message": "Kafka consumer stats reset",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Reset Kafka stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
