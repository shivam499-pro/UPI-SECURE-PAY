"""
UPI Secure Pay AI - FastAPI Main Application
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import get_settings
from app.database import init_db, close_db
from app.cache import close_redis
from app.kafka.producer import close_producer
from app.ml import get_ml_service

from app.routers import health, fraud, analytics

settings = get_settings()

# Application start time for uptime calculation
start_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting UPI Secure Pay AI Backend...")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
    
    # Load ML models
    try:
        ml_service = await get_ml_service()
        logger.info(f"ML models loaded: {ml_service.is_loaded}")
    except Exception as e:
        logger.warning(f"ML model loading failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down UPI Secure Pay AI Backend...")
    
    # Close connections
    await close_db()
    await close_redis()
    await close_producer()
    
    logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Real-time fraud detection API for UPI transactions",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(fraud.router, prefix="/api/v1", tags=["Fraud Detection"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to responses"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Simple health check"""
    uptime = time.time() - start_time
    return {
        "status": "healthy",
        "version": settings.app_version,
        "uptime_seconds": uptime,
    }


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
