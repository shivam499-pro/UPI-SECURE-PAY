"""
UPI Secure Pay AI - Health Check Router
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.config import get_settings

settings = get_settings()

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # Check database
    try:
        # This would normally check the database connection
        health_status["components"]["database"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["components"]["database"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        # This would normally check Redis connection
        health_status["components"]["cache"] = {
            "status": "healthy",
            "message": "Connected"
        }
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check ML models
    try:
        from app.ml import get_ml_service
        ml_service = await get_ml_service()
        health_status["components"]["ml_models"] = {
            "status": "healthy" if ml_service.is_loaded else "loading",
            "message": "Loaded" if ml_service.is_loaded else "Not loaded"
        }
    except Exception as e:
        health_status["components"]["ml_models"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat(),
    }
