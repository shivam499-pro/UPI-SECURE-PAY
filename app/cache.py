"""
UPI Secure Pay AI - Redis Cache Layer
"""

import json
import redis.asyncio as redis
from typing import Optional, Any
from datetime import timedelta

from app.config import get_settings

settings = get_settings()

# Redis client
redis_client: Optional[redis.Redis] = None


class CacheKeys:
    """Cache key patterns"""
    
    # User patterns
    @staticmethod
    def user_risk(user_id: str) -> str:
        return f"user:{user_id}:risk"
    
    @staticmethod
    def user_history(user_id: str) -> str:
        return f"user:{user_id}:history"
    
    @staticmethod
    def user_features(user_id: str) -> str:
        return f"user:{user_id}:features"
    
    # Device patterns
    @staticmethod
    def device_risk(device_id: str) -> str:
        return f"device:{device_id}:risk"
    
    @staticmethod
    def device_info(device_id: str) -> str:
        return f"device:{device_id}:info"
    
    # Merchant patterns
    @staticmethod
    def merchant_info(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:info"
    
    @staticmethod
    def merchant_risk(merchant_id: str) -> str:
        return f"merchant:{merchant_id}:risk"
    
    # Feature cache
    @staticmethod
    def transaction_features(transaction_id: str) -> str:
        return f"features:{transaction_id}"
    
    # Model cache
    @staticmethod
    def model_prediction(transaction_id: str) -> str:
        return f"prediction:{transaction_id}"


class CacheTTL:
    """Cache TTL values in seconds"""
    USER_RISK = 3600  # 1 hour
    USER_HISTORY = 1800  # 30 minutes
    DEVICE_RISK = 7200  # 2 hours
    DEVICE_INFO = 3600  # 1 hour
    MERCHANT_INFO = 3600  # 1 hour
    FEATURES = 60  # 1 minute
    PREDICTION = 300  # 5 minutes


async def get_redis() -> redis.Redis:
    """Get Redis client"""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True,
        )
    return redis_client


async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None


# ==================== Cache Operations ====================

async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """Set value in cache"""
    try:
        client = await get_redis()
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await client.setex(key, ttl, value)
        return True
    except Exception as e:
        print(f"Cache set error: {e}")
        return False


async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache"""
    try:
        client = await get_redis()
        value = await client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None


async def cache_delete(key: str) -> bool:
    """Delete key from cache"""
    try:
        client = await get_redis()
        await client.delete(key)
        return True
    except Exception as e:
        print(f"Cache delete error: {e}")
        return False


async def cache_exists(key: str) -> bool:
    """Check if key exists"""
    try:
        client = await get_redis()
        return await client.exists(key) > 0
    except Exception as e:
        print(f"Cache exists error: {e}")
        return False


# ==================== User Cache Operations ====================

async def get_user_risk(user_id: str) -> Optional[dict]:
    """Get user risk from cache"""
    return await cache_get(CacheKeys.user_risk(user_id))


async def set_user_risk(user_id: str, risk_data: dict) -> bool:
    """Cache user risk data"""
    return await cache_set(
        CacheKeys.user_risk(user_id),
        risk_data,
        CacheTTL.USER_RISK
    )


async def get_user_history(user_id: str) -> Optional[list]:
    """Get user transaction history from cache"""
    return await cache_get(CacheKeys.user_history(user_id))


async def set_user_history(user_id: str, history: list) -> bool:
    """Cache user transaction history"""
    return await cache_set(
        CacheKeys.user_history(user_id),
        history,
        CacheTTL.USER_HISTORY
    )


# ==================== Device Cache Operations ====================

async def get_device_risk(device_id: str) -> Optional[dict]:
    """Get device risk from cache"""
    return await cache_get(CacheKeys.device_risk(device_id))


async def set_device_risk(device_id: str, risk_data: dict) -> bool:
    """Cache device risk data"""
    return await cache_set(
        CacheKeys.device_risk(device_id),
        risk_data,
        CacheTTL.DEVICE_RISK
    )


async def get_device_info(device_id: str) -> Optional[dict]:
    """Get device info from cache"""
    return await cache_get(CacheKeys.device_info(device_id))


async def set_device_info(device_id: str, device_data: dict) -> bool:
    """Cache device info"""
    return await cache_set(
        CacheKeys.device_info(device_id),
        device_data,
        CacheTTL.DEVICE_INFO
    )


# ==================== Merchant Cache Operations ====================

async def get_merchant_info(merchant_id: str) -> Optional[dict]:
    """Get merchant info from cache"""
    return await cache_get(CacheKeys.merchant_info(merchant_id))


async def set_merchant_info(merchant_id: str, merchant_data: dict) -> bool:
    """Cache merchant info"""
    return await cache_set(
        CacheKeys.merchant_info(merchant_id),
        merchant_data,
        CacheTTL.MERCHANT_INFO
    )


# ==================== Feature Cache Operations ====================

async def get_transaction_features(transaction_id: str) -> Optional[dict]:
    """Get transaction features from cache"""
    return await cache_get(CacheKeys.transaction_features(transaction_id))


async def set_transaction_features(transaction_id: str, features: dict) -> bool:
    """Cache transaction features"""
    return await cache_set(
        CacheKeys.transaction_features(transaction_id),
        features,
        CacheTTL.FEATURES
    )


# ==================== Model Prediction Cache ====================

async def get_prediction(transaction_id: str) -> Optional[dict]:
    """Get cached prediction"""
    return await cache_get(CacheKeys.model_prediction(transaction_id))


async def set_prediction(transaction_id: str, prediction: dict) -> bool:
    """Cache model prediction"""
    return await cache_set(
        CacheKeys.model_prediction(transaction_id),
        prediction,
        CacheTTL.PREDICTION
    )


# ==================== Rate Limiting ====================

async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    """Check rate limit using sliding window"""
    try:
        client = await get_redis()
        current = await client.incr(key)
        
        if current == 1:
            await client.expire(key, window)
        
        return current <= limit
    except Exception as e:
        print(f"Rate limit error: {e}")
        return True  # Allow if rate limiting fails
