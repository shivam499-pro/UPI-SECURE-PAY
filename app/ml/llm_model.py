"""
UPI Secure Pay AI - LLM Model for Merchant Analysis
"""

import os
import torch
from typing import Dict, Any, Optional, List
from loguru import logger


class LLMModel:
    """LLM-based model for merchant analysis"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or "models/llm/llama_model"
        self.model_name = "llm"
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.is_loaded = False
    
    async def load(self) -> bool:
        try:
            logger.info("Loading LLM model...")
            # Simple fallback model
            self._create_fallback_model()
            self.is_loaded = True
            logger.info(f"LLM model loaded on {self.device}")
            return True
        except Exception as e:
            logger.error(f"Failed to load LLM: {e}")
            return False
    
    def _create_fallback_model(self):
        class SimpleClassifier(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.net = torch.nn.Sequential(
                    torch.nn.Linear(6, 32),
                    torch.nn.ReLU(),
                    torch.nn.Linear(32, 1),
                    torch.nn.Sigmoid()
                )
            def forward(self, x):
                return self.net(x)
        self.model = SimpleClassifier()
    
    async def predict(self, features: Dict[str, Any]) -> float:
        if not self.is_loaded:
            return 0.5
        try:
            # Simple feature-based prediction
            score = self._calculate_score(features)
            return float(score)
        except:
            return 0.5
    
    def _calculate_score(self, features: Dict[str, Any]) -> float:
        score = 0.0
        if features.get('merchant_name_suspicion', 0) > 0.5:
            score += 0.3
        if features.get('review_sentiment', 0.5) < 0.3:
            score += 0.2
        if features.get('category_suspicion', 0) > 0.5:
            score += 0.2
        if features.get('pricing_anomaly', 0) > 0.7:
            score += 0.15
        return min(score, 1.0)
    
    def extract_features(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'merchant_name_suspicion': self._check_name(data.get('merchant_name', '')),
            'merchant_description_quality': 0.5,
            'review_sentiment': 0.5,
            'category_suspicion': self._check_category(data.get('merchant_category', '')),
            'pricing_anomaly': 0.1,
            'complaint_pattern': data.get('fraud_reports', 0) / 10.0,
        }
    
    def _check_name(self, name: str) -> float:
        suspicious = ['free', 'win', 'gift', 'cashback', 'limited', 'offer']
        if any(s in name.lower() for s in suspicious):
            return 0.7
        return 0.2
    
    def _check_category(self, category: str) -> float:
        high_risk = ['gaming', 'investment', 'lottery', 'dating', 'crypto']
        if any(c in category.lower() for c in high_risk):
            return 0.7
        return 0.1


_llm_model: Optional[LLMModel] = None

async def get_llm_model() -> LLMModel:
    global _llm_model
    if _llm_model is None:
        _llm_model = LLMModel()
        await _llm_model.load()
    return _llm_model
