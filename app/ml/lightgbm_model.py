"""
UPI Secure Pay AI - LightGBM Model Implementation
"""

import os
import json
import lightgbm as lgb
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.ml.base import BaseFraudModel
from app.config import get_settings

settings = get_settings()


class LightGBMModel(BaseFraudModel):
    """LightGBM fraud detection model"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(
            model_path=model_path or settings.lightgbm_model_path,
            model_name="lightgbm"
        )
        
        # Define features for LightGBM
        self.features = [
            # Transaction features
            "amount",
            "amount_log",
            "hour",
            "day_of_week",
            "is_weekend",
            "is_night",
            
            # User features
            "user_account_age_days",
            "user_transaction_count_30d",
            "user_avg_amount_30d",
            "user_max_amount_30d",
            "user_transaction_count_1d",
            
            # Device features
            "device_is_new",
            "device_is_rooted",
            "device_transaction_count",
            
            # Merchant features
            "merchant_risk_score",
            "merchant_fraud_reports",
            "merchant_is_verified",
            
            # Receiver features
            "receiver_transaction_count_30d",
            "receiver_avg_amount_30d",
            "receiver_is_new",
            
            # Network features
            "sender_receiver_same_bank",
            "transaction_velocity_1h",
            "transaction_velocity_24h",
        ]
    
    async def load(self) -> bool:
        """Load LightGBM model from file"""
        try:
            if not os.path.exists(self.model_path):
                logger.warning(f"LightGBM model file not found: {self.model_path}")
                logger.info("Creating dummy model for development")
                # Create a simple model for development
                self.model = lgb.LGBMClassifier(
                    n_estimators=100,
                    max_depth=6,
                    learning_rate=0.1,
                    random_state=42
                )
                # Fit with dummy data
                X_dummy = np.random.rand(1000, len(self.features))
                y_dummy = np.random.randint(0, 2, 1000)
                self.model.fit(X_dummy, y_dummy)
            else:
                self.model = lgb.Booster(model_file=self.model_path)
            
            self.is_loaded = True
            logger.info(f"LightGBM model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load LightGBM model: {e}")
            self.is_loaded = False
            return False
    
    async def predict(self, features: Dict[str, Any]) -> float:
        """Make prediction using LightGBM
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            float: Fraud probability between 0 and 1
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # Extract features in correct order
            feature_vector = self._prepare_features(features)
            
            # Get prediction probability
            if hasattr(self.model, 'predict_proba'):
                prob = self.model.predict_proba([feature_vector])[0][1]
            else:
                # For Booster
                prob = self.model.predict([feature_vector])[0]
            
            return float(prob)
            
        except Exception as e:
            logger.error(f"LightGBM prediction error: {e}")
            return 0.5  # Return neutral score on error
    
    def _prepare_features(self, features: Dict[str, Any]) -> list:
        """Prepare feature vector in correct order"""
        return [features.get(f, 0) for f in self.features]
    
    def extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from transaction data
        
        Args:
            transaction_data: Raw transaction data from API
            
        Returns:
            Dict: Extracted features for model input
        """
        features = {}
        
        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(transaction_data.get('timestamp', '').replace('Z', '+00:00'))
            hour = timestamp.hour
            features['hour'] = hour
            features['day_of_week'] = timestamp.weekday()
            features['is_weekend'] = 1 if timestamp.weekday() >= 5 else 0
            features['is_night'] = 1 if (hour >= 22 or hour < 6) else 0
        except:
            features['hour'] = 12
            features['day_of_week'] = 0
            features['is_weekend'] = 0
            features['is_night'] = 0
        
        # Transaction features
        amount = transaction_data.get('amount', 0)
        features['amount'] = amount
        features['amount_log'] = np.log1p(amount) if amount > 0 else 0
        
        # User features (from transaction data)
        features['user_account_age_days'] = transaction_data.get('user_account_age_days', 365)
        features['user_transaction_count_30d'] = transaction_data.get('user_transaction_count_30d', 10)
        features['user_avg_amount_30d'] = transaction_data.get('user_avg_amount_30d', amount)
        features['user_max_amount_30d'] = transaction_data.get('user_max_amount_30d', amount)
        features['user_transaction_count_1d'] = transaction_data.get('user_transaction_count_1d', 1)
        
        # Device features
        features['device_is_new'] = 1 if transaction_data.get('device_first_seen_days', 0) < 7 else 0
        features['device_is_rooted'] = 1 if transaction_data.get('device_is_rooted', False) else 0
        features['device_transaction_count'] = transaction_data.get('device_transaction_count', 1)
        
        # Merchant features
        features['merchant_risk_score'] = transaction_data.get('merchant_risk_score', 0.0)
        features['merchant_fraud_reports'] = transaction_data.get('merchant_fraud_reports', 0)
        features['merchant_is_verified'] = 1 if transaction_data.get('merchant_verified', False) else 0
        
        # Receiver features
        features['receiver_transaction_count_30d'] = transaction_data.get('receiver_transaction_count_30d', 10)
        features['receiver_avg_amount_30d'] = transaction_data.get('receiver_avg_amount_30d', amount)
        features['receiver_is_new'] = 1 if transaction_data.get('receiver_account_age_days', 0) < 30 else 0
        
        # Network features
        features['sender_receiver_same_bank'] = 1 if transaction_data.get('sender_bank', '') == transaction_data.get('receiver_bank', '') else 0
        features['transaction_velocity_1h'] = transaction_data.get('transaction_velocity_1h', 0)
        features['transaction_velocity_24h'] = transaction_data.get('transaction_velocity_24h', 0)
        
        return features
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if not self.is_loaded or self.model is None:
            return {}
        
        try:
            importance = self.model.feature_importance(importance_type='gain')
            return dict(zip(self.features, importance.tolist()))
        except:
            return {}


# Singleton instance
_lightgbm_model: Optional[LightGBMModel] = None


async def get_lightgbm_model() -> LightGBMModel:
    """Get LightGBM model singleton"""
    global _lightgbm_model
    if _lightgbm_model is None:
        _lightgbm_model = LightGBMModel()
        await _lightgbm_model.load()
    return _lightgbm_model
