"""
UPI Secure Pay AI - ML Service (Ensemble of ALL 5 Models)
"""

from typing import Dict, Any, Optional
import time
from loguru import logger

from app.ml.lightgbm_model import LightGBMModel, get_lightgbm_model
from app.ml.transformer_model import TransformerModel, get_transformer_model
from app.ml.gnn_model import GNNModel, get_gnn_model
from app.ml.tgn_model import TGNModel, get_tgn_model
from app.ml.llm_model import LLMModel, get_llm_model
from app.config import get_settings
from app.models.response import FraudScoreModel

settings = get_settings()


class MLService:
    """ML Service that combines ALL 5 models for fraud detection"""
    
    def __init__(self):
        self.lightgbm: Optional[LightGBMModel] = None
        self.transformer: Optional[TransformerModel] = None
        self.gnn: Optional[GNNModel] = None
        self.tgn: Optional[TGNModel] = None
        self.llm: Optional[LLMModel] = None
        self.is_loaded = False
        
        # Ensemble weights - Core: 50%, Supporting: 50%
        self.ensemble_weights = {
            "lightgbm": 0.25,    # Core
            "transformer": 0.25,  # Core
            "gnn": 0.20,         # Supporting
            "tgn": 0.15,        # Supporting
            "llm": 0.15,        # Supporting
        }
    
    async def load_models(self) -> bool:
        """Load ALL ML models"""
        try:
            logger.info("Loading ALL ML models...")
            
            # Core Models
            self.lightgbm = await get_lightgbm_model()
            logger.info(f"LightGBM loaded: {self.lightgbm.is_loaded}")
            
            self.transformer = await get_transformer_model()
            logger.info(f"Transformer loaded: {self.transformer.is_loaded}")
            
            # Supporting Models
            self.gnn = await get_gnn_model()
            logger.info(f"GNN loaded: {self.gnn.is_loaded}")
            
            self.tgn = await get_tgn_model()
            logger.info(f"TGN loaded: {self.tgn.is_loaded}")
            
            self.llm = await get_llm_model()
            logger.info(f"LLM loaded: {self.llm.is_loaded}")
            
            self.is_loaded = all([
                self.lightgbm.is_loaded,
                self.transformer.is_loaded,
                self.gnn.is_loaded,
                self.tgn.is_loaded,
                self.llm.is_loaded,
            ])
            
            logger.info(f"ALL ML models loaded: {self.is_loaded}")
            return self.is_loaded
            
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            return False
    
    async def predict(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make ensemble prediction using ALL 5 models"""
        
        start_time = time.time()
        
        try:
            # Get predictions from all models
            model_scores = []
            total_score = 0.0
            
            # 1. LightGBM
            lgb_features = self.lightgbm.extract_features(transaction_data)
            lgb_score = await self.lightgbm.predict(lgb_features)
            model_scores.append(FraudScoreModel(
                model_name="lightgbm",
                score=lgb_score,
                weight=self.ensemble_weights["lightgbm"],
                features_used=list(lgb_features.keys())[:10]
            ))
            total_score += lgb_score * self.ensemble_weights["lightgbm"]
            
            # 2. Transformer
            trans_features = self.transformer.extract_features(transaction_data)
            trans_score = await self.transformer.predict(trans_features)
            model_scores.append(FraudScoreModel(
                model_name="transformer",
                score=trans_score,
                weight=self.ensemble_weights["transformer"],
                features_used=list(trans_features.keys())[:10]
            ))
            total_score += trans_score * self.ensemble_weights["transformer"]
            
            # 3. GNN
            gnn_features = self.gnn.extract_features(transaction_data)
            gnn_score = await self.gnn.predict(gnn_features)
            model_scores.append(FraudScoreModel(
                model_name="gnn",
                score=gnn_score,
                weight=self.ensemble_weights["gnn"],
                features_used=list(gnn_features.keys())[:10]
            ))
            total_score += gnn_score * self.ensemble_weights["gnn"]
            
            # 4. TGN
            tgn_features = self.tgn.extract_features(transaction_data)
            tgn_score = await self.tgn.predict(tgn_features)
            model_scores.append(FraudScoreModel(
                model_name="tgn",
                score=tgn_score,
                weight=self.ensemble_weights["tgn"],
                features_used=list(tgn_features.keys())[:10]
            ))
            total_score += tgn_score * self.ensemble_weights["tgn"]
            
            # 5. LLM (for merchant analysis)
            llm_features = self.llm.extract_features(transaction_data)
            llm_score = await self.llm.predict(llm_features)
            model_scores.append(FraudScoreModel(
                model_name="llm",
                score=llm_score,
                weight=self.ensemble_weights["llm"],
                features_used=list(llm_features.keys())[:10]
            ))
            total_score += llm_score * self.ensemble_weights["llm"]
            
            # Final risk score (0-100)
            risk_score = total_score * 100
            
            # Decision
            if risk_score >= settings.fraud_threshold_block:
                decision = "block"
            elif risk_score >= settings.fraud_threshold_review:
                decision = "verify"
            else:
                decision = "proceed"
            
            # Generate reasons
            reasons = self._generate_reasons(transaction_data, model_scores)
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "risk_score": risk_score,
                "decision": decision,
                "model_scores": model_scores,
                "reasons": reasons,
                "processing_time_ms": processing_time,
            }
            
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return {
                "risk_score": 50.0,
                "decision": "verify",
                "model_scores": [],
                "reasons": ["Error in fraud detection"],
                "processing_time_ms": (time.time() - start_time) * 1000,
            }
    
    def _generate_reasons(self, transaction_data: Dict[str, Any], model_scores: list) -> list:
        """Generate reasons for the decision"""
        reasons = []
        
        amount = transaction_data.get('amount', 0)
        if amount > 50000:
            reasons.append(f"High amount: ₹{amount:,}")
        
        try:
            from datetime import datetime
            ts = transaction_data.get('timestamp', '')
            if ts:
                timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                if timestamp.hour >= 22 or timestamp.hour < 6:
                    reasons.append("Unusual transaction time (night)")
        except:
            pass
        
        # Check high scores from models
        for ms in model_scores:
            if ms.score > 0.7:
                reasons.append(f"High {ms.model_name} score: {ms.score:.2f}")
        
        if not reasons:
            reasons.append("Transaction appears normal")
        
        return reasons
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "is_loaded": self.is_loaded,
            "models": {
                "lightgbm": self.lightgbm.is_loaded if self.lightgbm else False,
                "transformer": self.transformer.is_loaded if self.transformer else False,
                "gnn": self.gnn.is_loaded if self.gnn else False,
                "tgn": self.tgn.is_loaded if self.tgn else False,
                "llm": self.llm.is_loaded if self.llm else False,
            },
            "ensemble_weights": self.ensemble_weights,
            "thresholds": {
                "block": settings.fraud_threshold_block,
                "review": settings.fraud_threshold_review,
            },
            "core_models": ["lightgbm", "transformer"],
            "supporting_models": ["gnn", "tgn", "llm"],
        }


_ml_service: Optional[MLService] = None

async def get_ml_service() -> MLService:
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService()
        await _ml_service.load_models()
    return _ml_service
