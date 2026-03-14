"""
UPI Secure Pay AI - Kafka Package
"""

from app.kafka.producer import (
    get_producer,
    close_producer,
    publish_transaction,
    publish_scored_transaction,
    publish_alert,
    Topics,
    KafkaProducerService,
)

from app.kafka.consumer import (
    start_consumer,
    stop_consumer,
    consume_messages,
    get_consumer_stats,
    reset_consumer_stats,
    consumer_stats,
)

__all__ = [
    # Producer
    "get_producer",
    "close_producer", 
    "publish_transaction",
    "publish_scored_transaction",
    "publish_alert",
    "Topics",
    "KafkaProducerService",
    # Consumer
    "start_consumer",
    "stop_consumer",
    "consume_messages",
    "get_consumer_stats",
    "reset_consumer_stats",
    "consumer_stats",
]
