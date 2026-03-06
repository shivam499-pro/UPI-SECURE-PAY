"""
UPI Secure Pay AI - Fraud Detection Router
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from loguru import logger

from app.models.request import FraudCheckRequest, FeedbackRequest, BatchFraudCheckRequest
from app.models.response import FraudCheckResponse, FeedbackResponse, ErrorResponse
from app.ml import get_ml_service
from app.cache import cache_get, cache_set
from app.kafka.producer import publish_transaction, publish_scored_transaction, publish_alert

router = APIRouter()


@router.post("/fraud-check", response_model=FraudCheckResponse)
async def check_fraud(request: FraudCheckRequest):
    """
    Main fraud detection endpoint.
    
    Checks a transaction for fraud using the ensemble of ML models.
    """
    try:
        # Generate transaction ID if not provided
        transaction_id = f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        
        # Check cache first (for duplicate requests)
        cached_result = await cache_get(f"fraud_check:{transaction_id}")
        if cached_result:
            logger.info(f"Returning cached result for transaction {transaction_id}")
            return cached_result
        
        # Get ML service
        ml_service = await get_ml_service()
        
        # Convert request to dict
        transaction_data = request.transaction.dict()
        transaction_data['transaction_id'] = transaction_id
        
        # Make prediction
        result = await ml_service.predict(transaction_data)
        
        # Map decision to status
        status_map = {
            "proceed": "approved",
            "verify": "review", 
            "block": "blocked"
        }
        
        # Build response
        response = FraudCheckResponse(
            transaction_id=transaction_id,
            status=status_map.get(result['decision'], "review"),
            risk_score=round(result['risk_score'], 2),
            decision=result['decision'],
            reasons=result['reasons'],
            model_scores=result['model_scores'],
            processing_time_ms=round(result['processing_time_ms'], 2),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Cache the result
        await cache_set(f"fraud_check:{transaction_id}", response.dict(), ttl=300)
        
        # Publish to Kafka (async, don't wait)
        try:
            await publish_transaction(transaction_data)
            await publish_scored_transaction({
                **transaction_data,
                'fraud_score': result['risk_score'],
                'decision': result['decision'],
                'model_scores': [ms.dict() for ms in result['model_scores']],
                'reasons': result['reasons'],
                'processed_at': datetime.utcnow().isoformat()
            })
            
            # Publish alert if blocked
            if result['decision'] == 'block':
                await publish_alert({
                    'transaction_id': transaction_id,
                    'alert_type': 'HIGH_RISK_TRANSACTION',
                    'severity': 'critical',
                    'risk_score': result['risk_score'],
                    'reasons': result['reasons'],
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"Fraud check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/fraud-check/batch", response_model=dict)
async def batch_check_fraud(request: BatchFraudCheckRequest):
    """
    Batch fraud detection endpoint.
    
    Checks multiple transactions for fraud.
    """
    try:
        results = []
        
        for transaction in request.transactions:
            transaction_id = f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
            
            # Get ML service
            ml_service = await get_ml_service()
            
            # Convert to dict
            transaction_data = transaction.dict()
            transaction_data['transaction_id'] = transaction_id
            
            # Make prediction
            result = await ml_service.predict(transaction_data)
            
            results.append({
                'transaction_id': transaction_id,
                'risk_score': result['risk_score'],
                'decision': result['decision'],
                'reasons': result['reasons']
            })
        
        return {
            'total_transactions': len(request.transactions),
            'results': results,
            'timestamp': datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Batch fraud check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback on fraud detection decisions.
    
    Used to improve the model over time.
    """
    try:
        # Process feedback
        logger.info(f"Received feedback for transaction {request.transaction_id}: is_correct={request.is_correct}")
        
        # In production, this would:
        # 1. Store the feedback in database
        # 2. Trigger model retraining if needed
        # 3. Update feature store
        
        return FeedbackResponse(
            status="success",
            message="Feedback received and will be used for model improvement",
            feedback_id=12345  # In production, return actual ID
        )
        
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/transaction/{transaction_id}")
async def get_transaction(transaction_id: str):
    """
    Get transaction details by ID.
    """
    try:
        # Check cache first
        cached = await cache_get(f"transaction:{transaction_id}")
        if cached:
            return cached
        
        # In production, fetch from database
        # For now, return not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get transaction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/models/status")
async def get_models_status():
    """
    Get status of ML models.
    """
    try:
        ml_service = await get_ml_service()
        status = ml_service.get_status()
        
        return {
            "models_loaded": status["is_loaded"],
            "lightgbm": status["models"]["lightgbm"],
            "transformer": status["models"]["transformer"],
            "ensemble_weights": status["ensemble_weights"],
            "thresholds": status["thresholds"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Get models status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
