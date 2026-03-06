"""
UPI Secure Pay AI - Base ML Model Class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
from loguru import logger


class BaseFraudModel(ABC):
    """Base class for fraud detection models"""
    
    def __init__(self, model_path: str, model_name: str):
        self.model_path = model_path
        self.model_name = model_name
        self.model = None
        self.is_loaded = False
        self.features: list = []
    
    @abstractmethod
    async def load(self) -> bool:
        """Load the model from disk"""
        pass
    
    @abstractmethod
    async def predict(self, features: Dict[str, Any]) -> float:
        """Make prediction on features
        
        Returns:
            float: Fraud probability between 0 and 1
        """
        pass
    
    @abstractmethod
    def extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features from transaction data
        
        Args:
            transaction_data: Raw transaction data
            
        Returns:
            Dict: Extracted features for model input
        """
        pass
    
    async def unload(self):
        """Unload the model from memory"""
        self.model = None
        self.is_loaded = False
        logger.info(f"Model {self.model_name} unloaded")
    
    def validate_features(self, features: Dict[str, Any]) -> bool:
        """Validate that all required features are present"""
        missing = set(self.features) - set(features.keys())
        if missing:
            logger.warning(f"Missing features for {self.model_name}: {missing}")
            return False
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "features": self.features,
        }

    def get_status(self) -> Dict[str, Any]:
        """Get model status - override in subclass for detailed status"""
        return {
            "name": self.model_name,
            "loaded": self.is_loaded,
            "path": self.model_path,
        }
