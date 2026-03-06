"""
UPI Secure Pay AI - Temporal Graph Network (TGN) Model Implementation
"""

import os
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger

from app.ml.base import BaseFraudModel
from app.config import get_settings

settings = get_settings()


class TGNModel(BaseFraudModel):
    """Temporal Graph Network for time-aware fraud detection"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(
            model_path=model_path or "models/tgn/fraud_tgn.pt",
            model_name="tgn"
        )
        
        # Features for temporal analysis
        self.features = [
            # Transaction timing
            "time_since_last_transaction",
            "transaction_frequency_1h",
            "transaction_frequency_24h",
            "time_of_day",
            "day_of_week",
            "is_night",
            
            # Velocity patterns
            "velocity_5min",
            "velocity_15min",
            "velocity_1h",
            "velocity_24h",
            
            # Money flow patterns
            "avg_receive_to_send_time",
            "receive_send_ratio_1h",
            "receive_send_ratio_24h",
            
            # Sequence patterns
            "amount_increasing",
            "amount_stable",
            "amount_decreasing",
        ]
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tgn_model = None
        self.memory_module = None
    
    async def load(self) -> bool:
        """Load TGN model from file"""
        try:
            logger.info("Loading TGN model...")
            
            # Try to load pre-trained model
            if os.path.exists(self.model_path):
                self.tgn_model = torch.load(self.model_path, map_location=self.device)
            else:
                # Create a simple TGN model
                self._create_model()
            
            self.is_loaded = True
            logger.info(f"TGN model loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load TGN model: {e}")
            self.is_loaded = False
            return False
    
    def _create_model(self):
        """Create a simple Temporal Graph Network model"""
        
        class TemporalEncoder(nn.Module):
            def __init__(self, input_dim: int, hidden_dim: int, time_dim: int = 8):
                super().__init__()
                self.time_encoder = nn.Linear(time_dim, hidden_dim)  # Encode all 8 time features
                self.feature_encoder = nn.Linear(input_dim, hidden_dim)
                self.attention = nn.MultiheadAttention(hidden_dim, num_heads=4)
                self.output = nn.Sequential(
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(0.2),
                    nn.Linear(hidden_dim, 1),
                    nn.Sigmoid()
                )
            
            def forward(self, x, time_deltas):
                # Encode time information (time_deltas shape: [batch, 8])
                time_encoded = self.time_encoder(time_deltas)
                
                # Encode features
                feature_encoded = self.feature_encoder(x)
                
                # Combine
                combined = time_encoded + feature_encoded
                
                # Apply attention
                attn_output, _ = self.attention(combined, combined, combined)
                
                # Output
                output = self.output(attn_output)
                return output.squeeze(-1)
        
        # Create model
        self.tgn_model = TemporalEncoder(
            input_dim=len(self.features),
            hidden_dim=64
        )
        
        logger.info("Created simple TGN model")
    
    async def predict(self, features: Dict[str, Any]) -> float:
        """Make prediction using TGN
        
        Args:
            features: Dictionary containing temporal features
            
        Returns:
            float: Fraud probability between 0 and 1
        """
        if not self.is_loaded:
            raise RuntimeError("TGN model not loaded")
        
        try:
            # Extract features
            feature_vector = self._prepare_features(features)
            time_deltas = self._get_time_deltas(features)
            
            # Convert to tensors
            x = torch.FloatTensor([feature_vector]).to(self.device)
            time_deltas = torch.FloatTensor([time_deltas]).to(self.device)
            
            # Get prediction
            with torch.no_grad():
                prob = self.tgn_model(x, time_deltas).item()
            
            return float(prob)
            
        except Exception as e:
            logger.error(f"TGN prediction error: {e}")
            return 0.5
    
    def _prepare_features(self, features: Dict[str, Any]) -> List[float]:
        """Prepare feature vector"""
        return [features.get(f, 0.0) for f in self.features]
    
    def _get_time_deltas(self, features: Dict[str, Any]) -> List[float]:
        """Get time deltas for temporal encoding"""
        # Normalize time deltas to hours
        return [
            features.get('time_since_last_transaction', 3600) / 3600.0,
            features.get('transaction_frequency_1h', 1) / 10.0,
            features.get('transaction_frequency_24h', 10) / 100.0,
            features.get('velocity_5min', 0) / 5.0,
            features.get('velocity_15min', 0) / 15.0,
            features.get('velocity_1h', 0) / 10.0,
            features.get('velocity_24h', 0) / 50.0,
            features.get('avg_receive_to_send_time', 3600) / 86400.0,
        ]
    
    def extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract temporal features from transaction data
        
        Args:
            transaction_data: Raw transaction data
            
        Returns:
            Dict: Extracted temporal features
        """
        features = {}
        
        # Parse timestamp
        try:
            timestamp = datetime.fromisoformat(transaction_data.get('timestamp', '').replace('Z', '+00:00'))
            
            # Time features
            features['time_of_day'] = timestamp.hour / 24.0
            features['day_of_week'] = timestamp.weekday() / 7.0
            features['is_night'] = 1.0 if (timestamp.hour >= 22 or timestamp.hour < 6) else 0.0
        except:
            features['time_of_day'] = 0.5
            features['day_of_week'] = 0.0
            features['is_night'] = 0.0
        
        # Transaction timing
        features['time_since_last_transaction'] = transaction_data.get('time_since_last_transaction', 3600)
        features['transaction_frequency_1h'] = transaction_data.get('transaction_frequency_1h', 1)
        features['transaction_frequency_24h'] = transaction_data.get('transaction_frequency_24h', 10)
        
        # Velocity patterns
        features['velocity_5min'] = transaction_data.get('velocity_5min', 0)
        features['velocity_15min'] = transaction_data.get('velocity_15min', 0)
        features['velocity_1h'] = transaction_data.get('velocity_1h', 0)
        features['velocity_24h'] = transaction_data.get('velocity_24h', 0)
        
        # Money flow patterns
        features['avg_receive_to_send_time'] = transaction_data.get('avg_receive_to_send_time', 3600)
        features['receive_send_ratio_1h'] = transaction_data.get('receive_send_ratio_1h', 1.0)
        features['receive_send_ratio_24h'] = transaction_data.get('receive_send_ratio_24h', 1.0)
        
        # Sequence patterns
        features['amount_increasing'] = transaction_data.get('amount_increasing', 0.0)
        features['amount_stable'] = transaction_data.get('amount_stable', 1.0)
        features['amount_decreasing'] = transaction_data.get('amount_decreasing', 0.0)
        
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
_tgn_model: Optional[TGNModel] = None


async def get_tgn_model() -> TGNModel:
    """Get TGN model singleton"""
    global _tgn_model
    if _tgn_model is None:
        _tgn_model = TGNModel()
        await _tgn_model.load()
    return _tgn_model
