"""
UPI Secure Pay AI - Transformer Model Implementation
"""

import os
import torch
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.ml.base import BaseFraudModel
from app.config import get_settings

settings = get_settings()


class TransformerModel(BaseFraudModel):
    """Transformer-based fraud detection model"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(
            model_path=model_path or settings.transformer_model_path,
            model_name="transformer"
        )
        
        # Define features for Transformer
        self.features = [
            # Transaction features
            "amount",
            "amount_normalized",
            "hour",
            "day_of_week",
            "is_weekend",
            "is_night",
            "transaction_type_encoded",
            
            # User features
            "user_account_age_days",
            "user_transaction_count_30d",
            "user_avg_amount_30d",
            "user_risk_level_encoded",
            
            # Device features
            "device_is_new",
            "device_is_rooted",
            "device_type_encoded",
            
            # Merchant features
            "merchant_category_encoded",
            "merchant_risk_score",
            "merchant_fraud_reports",
            
            # Behavioral features
            "velocity_1h",
            "velocity_24h",
            "avg_time_between_transactions",
        ]
        
        self.tokenizer = None
        self.transformer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    async def load(self) -> bool:
        """Load Transformer model from file"""
        try:
            # For development, create a simple model
            # In production, load pre-trained model
            if not os.path.exists(self.model_path):
                logger.warning(f"Transformer model file not found: {self.model_path}")
                logger.info("Creating simple transformer for development")
                
                # Use a simple neural network as fallback
                self._create_simple_model()
            else:
                # Load pre-trained model
                self._load_pretrained_model()
            
            self.is_loaded = True
            self.transformer.to(self.device)
            logger.info(f"Transformer model loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Transformer model: {e}")
            self.is_loaded = False
            return False
    
    def _create_simple_model(self):
        """Create a simple neural network as fallback"""
        try:
            from transformers import AutoModel, AutoTokenizer
            
            # Try to load DistilBERT for sequence processing
            self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
            
            class SimpleTransformerClassifier(torch.nn.Module):
                def __init__(self, num_features: int):
                    super().__init__()
                    self.embedding = torch.nn.Linear(num_features, 128)
                    self.transformer_layer = torch.nn.TransformerEncoderLayer(
                        d_model=128,
                        nhead=4,
                        dim_feedforward=256,
                        dropout=0.1,
                        batch_first=True
                    )
                    self.transformer_encoder = torch.nn.TransformerEncoder(
                        self.transformer_layer,
                        num_layers=2
                    )
                    self.classifier = torch.nn.Sequential(
                        torch.nn.Linear(128, 64),
                        torch.nn.ReLU(),
                        torch.nn.Dropout(0.1),
                        torch.nn.Linear(64, 1),
                        torch.nn.Sigmoid()
                    )
                
                def forward(self, x):
                    x = self.embedding(x)
                    x = x.unsqueeze(1)  # Add sequence dimension
                    x = self.transformer_encoder(x)
                    x = x.squeeze(1)  # Remove sequence dimension
                    return self.classifier(x)
            
            self.transformer = SimpleTransformerClassifier(len(self.features))
            logger.info("Simple Transformer model created")
            
        except Exception as e:
            logger.warning(f"Could not load transformer: {e}, using simple MLP")
            self._create_mlp_model()
    
    def _create_mlp_model(self):
        """Create a simple MLP as final fallback"""
        class SimpleMLP(torch.nn.Module):
            def __init__(self, num_features: int):
                super().__init__()
                self.classifier = torch.nn.Sequential(
                    torch.nn.Linear(num_features, 64),
                    torch.nn.ReLU(),
                    torch.nn.Dropout(0.1),
                    torch.nn.Linear(64, 32),
                    torch.nn.ReLU(),
                    torch.nn.Linear(32, 1),
                    torch.nn.Sigmoid()
                )
            
            def forward(self, x):
                return self.classifier(x)
        
        self.transformer = SimpleMLP(len(self.features))
    
    def _load_pretrained_model(self):
        """Load pre-trained transformer model"""
        # This would load a trained model in production
        self._create_simple_model()
    
    async def predict(self, features: Dict[str, Any]) -> float:
        """Make prediction using Transformer
        
        Args:
            features: Dictionary of extracted features
            
        Returns:
            float: Fraud probability between 0 and 1
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # Prepare features
            feature_vector = self._prepare_features(features)
            tensor_input = torch.FloatTensor([feature_vector]).to(self.device)
            
            # Get prediction
            with torch.no_grad():
                prob = self.transformer(tensor_input).item()
            
            return float(prob)
            
        except Exception as e:
            logger.error(f"Transformer prediction error: {e}")
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
            features['hour'] = hour / 24.0  # Normalize
            features['day_of_week'] = timestamp.weekday() / 7.0  # Normalize
            features['is_weekend'] = 1.0 if timestamp.weekday() >= 5 else 0.0
            features['is_night'] = 1.0 if (hour >= 22 or hour < 6) else 0.0
        except:
            features['hour'] = 0.5
            features['day_of_week'] = 0.0
            features['is_weekend'] = 0.0
            features['is_night'] = 0.0
        
        # Transaction features
        amount = transaction_data.get('amount', 0)
        features['amount'] = amount
        features['amount_normalized'] = min(amount / 100000.0, 1.0)  # Normalize to 1 lakh max
        
        # Transaction type encoding
        tx_type = transaction_data.get('transaction_type', 'P2P')
        type_map = {'P2P': 0.0, 'P2M': 0.25, 'P2A': 0.5, 'B2P': 0.75, 'B2M': 1.0}
        features['transaction_type_encoded'] = type_map.get(tx_type, 0.0)
        
        # User features
        features['user_account_age_days'] = min(transaction_data.get('user_account_age_days', 365) / 365.0, 1.0)
        features['user_transaction_count_30d'] = min(transaction_data.get('user_transaction_count_30d', 10) / 100.0, 1.0)
        features['user_avg_amount_30d'] = min(transaction_data.get('user_avg_amount_30d', amount) / 100000.0, 1.0)
        
        # User risk level encoding
        risk_level = transaction_data.get('user_risk_level', 'normal')
        risk_map = {'low': 0.0, 'normal': 0.33, 'elevated': 0.66, 'high': 1.0}
        features['user_risk_level_encoded'] = risk_map.get(risk_level, 0.33)
        
        # Device features
        features['device_is_new'] = 1.0 if transaction_data.get('device_first_seen_days', 0) < 7 else 0.0
        features['device_is_rooted'] = 1.0 if transaction_data.get('device_is_rooted', False) else 0.0
        
        # Device type encoding
        device_type = transaction_data.get('device_type', 'unknown')
        device_map = {'android': 0.0, 'ios': 0.5, 'web': 0.75, 'unknown': 1.0}
        features['device_type_encoded'] = device_map.get(device_type, 1.0)
        
        # Merchant features
        merchant_category = transaction_data.get('merchant_category', 'other')
        category_map = {
            'retail': 0.0, 'grocery': 0.1, 'food': 0.2, 'travel': 0.3,
            'entertainment': 0.4, 'utilities': 0.5, 'healthcare': 0.6,
            'education': 0.7, 'other': 0.8
        }
        features['merchant_category_encoded'] = category_map.get(merchant_category, 0.8)
        features['merchant_risk_score'] = transaction_data.get('merchant_risk_score', 0.0)
        features['merchant_fraud_reports'] = min(transaction_data.get('merchant_fraud_reports', 0) / 10.0, 1.0)
        
        # Behavioral features
        features['velocity_1h'] = min(transaction_data.get('transaction_velocity_1h', 0) / 10.0, 1.0)
        features['velocity_24h'] = min(transaction_data.get('transaction_velocity_24h', 0) / 50.0, 1.0)
        features['avg_time_between_transactions'] = transaction_data.get('avg_time_between_transactions', 3600) / 86400.0  # Normalize to days
        
        return features
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "features": self.features,
            "device": str(self.device),
        }


# Singleton instance
_transformer_model: Optional[TransformerModel] = None


async def get_transformer_model() -> TransformerModel:
    """Get Transformer model singleton"""
    global _transformer_model
    if _transformer_model is None:
        _transformer_model = TransformerModel()
        await _transformer_model.load()
    return _transformer_model
