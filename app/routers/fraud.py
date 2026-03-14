"""
UPI Secure Pay AI - Fraud Detection Router
"""

import uuid
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from loguru import logger

from app.models.request import FraudCheckRequest, FeedbackRequest, BatchFraudCheckRequest
from app.models.response import FraudCheckResponse, FeedbackResponse, FraudScoreModel
from app.ml.orchestrator import get_fraud_cascade_engine, SafetyRuleEngine
from app.cache import cache_get, cache_set
from app.kafka.producer import publish_transaction, publish_scored_transaction, publish_alert
from app.database import get_db, Transaction
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

# Singleton safety engine for fallback
_safety_engine: Optional[SafetyRuleEngine] = None


def get_safety_engine() -> SafetyRuleEngine:
    """Get or create safety rule engine singleton"""
    global _safety_engine
    if _safety_engine is None:
        _safety_engine = SafetyRuleEngine()
    return _safety_engine


@router.post("/fraud-check", response_model=FraudCheckResponse)
async def check_fraud(request: FraudCheckRequest):
    """
    Main fraud detection endpoint.
    
    Uses FraudCascadeEngine with integrated SafetyRuleEngine:
    1. SafetyRuleEngine checks critical risk markers FIRST
    2. Level 1: LightGBM (if safety passes) - Fast filter
    3. Level 2: Transformer + TGN (if score 0.3-0.7) - Context analysis
    4. Level 3: GNN + LLaMA (if still suspicious) - Deep investigation
    """
    try:
        # Generate transaction ID if not provided
        transaction_id = f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
        
        # Check cache first (for duplicate requests)
        cached_result = await cache_get(f"fraud_check:{transaction_id}")
        if cached_result:
            logger.info(f"Returning cached result for transaction {transaction_id}")
            return FraudCheckResponse(**cached_result)
        
        # Convert request to dict for the engine
        transaction_data = request.transaction.dict()
        transaction_data['transaction_id'] = transaction_id
        
        try:
            # Get Fraud Cascade Engine (initialized at startup)
            cascade_engine = await get_fraud_cascade_engine()
            
            # Run cascaded inference
            result = await cascade_engine.predict(transaction_data)
            
            logger.info(f"Fraud check completed: {result['cascade_stage']} - {result['final_verdict']}")
            
        except Exception as e:
            logger.error(f"FraudCascadeEngine error: {e}")
            # Fallback to SafetyRuleEngine only if cascade fails
            logger.warning("Falling back to SafetyRuleEngine only")
            safety_engine = get_safety_engine()
            safety_result = safety_engine.check(transaction_data)
            
            result = {
                "final_verdict": "verify" if safety_result["is_critical"] else "proceed",
                "cascade_stage": "SAFETY_RULE_ENGINE_ONLY",
                "latency_ms": 1.0,
                "risk_score": 50.0 if safety_result["is_critical"] else 10.0,
                "model_scores": {},
                "levels_used": ["SafetyRuleEngine (FALLBACK)"],
                "safety_rules_triggered": safety_result["triggered_rules"],
                "decision_reason": f"Safety check: {', '.join(safety_result['triggered_rules']) or 'No rules triggered'}"
            }
        
        # Map decision to status
        status_map = {
            "proceed": "approved",
            "verify": "review", 
            "block": "blocked"
        }
        
        # Convert model_scores dict to list of FraudScoreModel
        model_scores_list = []
        if result.get('model_scores'):
            for model_name, score in result['model_scores'].items():
                model_scores_list.append(FraudScoreModel(
                    model_name=model_name,
                    score=score,
                    weight=0.2,  # Default weight for cascade
                    features_used=None
                ))
        
        # Build reasons list
        reasons = [result.get('decision_reason', 'No reason provided')]
        if result.get('safety_rules_triggered'):
            reasons = [f"Safety: {r}" for r in result['safety_rules_triggered']]
        
        # Build response
        response = FraudCheckResponse(
            transaction_id=transaction_id,
            status=status_map.get(result['final_verdict'], "review"),
            risk_score=round(result.get('risk_score', 0), 2),
            decision=result['final_verdict'],
            reasons=reasons,
            model_scores=model_scores_list,
            processing_time_ms=round(result.get('latency_ms', 0), 2),
            timestamp=datetime.utcnow().isoformat() + "Z",
            cascade_stage=result.get('cascade_stage'),
            safety_rules_triggered=result.get('safety_rules_triggered', []),
            levels_used=result.get('levels_used', [])
        )
        
        # Cache the result
        await cache_set(f"fraud_check:{transaction_id}", response.dict(), ttl=300)
        
        # Publish to Kafka (async, don't wait)
        try:
            await publish_transaction(transaction_data)
            await publish_scored_transaction({
                **transaction_data,
                'fraud_score': result.get('risk_score', 0),
                'decision': result.get('final_verdict', 'verify'),
                'cascade_stage': result.get('cascade_stage', 'UNKNOWN'),
                'safety_rules_triggered': result.get('safety_rules_triggered', []),
                'levels_used': result.get('levels_used', []),
                'processed_at': datetime.utcnow().isoformat()
            })
            
            # Publish alert if blocked or critical
            if result['final_verdict'] == 'block':
                await publish_alert({
                    'transaction_id': transaction_id,
                    'alert_type': 'HIGH_RISK_TRANSACTION',
                    'severity': 'critical',
                    'risk_score': result.get('risk_score', 0),
                    'cascade_stage': result.get('cascade_stage', 'UNKNOWN'),
                    'safety_rules': result.get('safety_rules_triggered', []),
                    'timestamp': datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
        
        # Save to database
        try:
            async for db in get_db():
                db_transaction = Transaction(
                    transaction_id=transaction_id,
                    sender_id=transaction_data.get('sender_id', ''),
                    sender_vpa=transaction_data.get('sender_vpa', ''),
                    receiver_id=transaction_data.get('receiver_id', ''),
                    receiver_vpa=transaction_data.get('receiver_vpa', ''),
                    amount=transaction_data.get('amount', 0),
                    timestamp=datetime.utcnow(),
                    status='completed',
                    fraud_score=result.get('risk_score', 0) / 100,  # Convert to 0-1 range
                    decision=result['final_verdict'],
                    device_id=transaction_data.get('sender_device_id', ''),
                    ip_address=transaction_data.get('ip_address', ''),
                    cascade_stage=result.get('cascade_stage'),
                    safety_rules_triggered=json.dumps(result.get('safety_rules_triggered', [])),
                    levels_used=json.dumps(result.get('levels_used', [])),
                    processing_time_ms=result.get('latency_ms', 0)
                )
                db.add(db_transaction)
                await db.commit()
                break
        except Exception as e:
            logger.error(f"Failed to save transaction to database: {e}")
        
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
    
    Checks multiple transactions for fraud using FraudCascadeEngine.
    """
    try:
        results = []
        cascade_engine = await get_fraud_cascade_engine()
        
        for transaction in request.transactions:
            transaction_id = f"TXN{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"
            
            # Convert to dict
            transaction_data = transaction.dict()
            transaction_data['transaction_id'] = transaction_id
            
            # Make prediction using cascade
            result = await cascade_engine.predict(transaction_data)
            
            results.append({
                'transaction_id': transaction_id,
                'risk_score': result.get('risk_score', 0),
                'decision': result.get('final_verdict', 'verify'),
                'cascade_stage': result.get('cascade_stage'),
                'safety_rules_triggered': result.get('safety_rules_triggered', [])
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
    Get status of ML models including FraudCascadeEngine.
    """
    try:
        cascade_engine = await get_fraud_cascade_engine()
        engine_info = cascade_engine.get_info() if cascade_engine.is_initialized else {}
        
        return {
            "cascade_engine_loaded": cascade_engine.is_initialized,
            "cascade_info": engine_info,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        logger.error(f"Get models status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
