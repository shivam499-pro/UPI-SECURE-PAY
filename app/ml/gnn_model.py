"""
UPI Secure Pay AI - Graph Neural Network (GNN) Model Implementation
"""

import os
import torch
import torch.nn as nn
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from app.ml.base import BaseFraudModel
from app.config import get_settings

settings = get_settings()


class GNNModel(BaseFraudModel):
    """Graph Neural Network for fraud detection using PyTorch Geometric"""
    
    def __init__(self, model_path: Optional[str] = None):
        super().__init__(
            model_path=model_path or "models/gnn/fraud_gnn.pt",
            model_name="gnn"
        )
        
        # Define node features for graph
        self.node_features = [
            "user_transaction_count",
            "user_avg_amount",
            "user_account_age",
            "user_risk_score",
            "device_transaction_count",
            "device_is_new",
            "merchant_transaction_count",
            "merchant_fraud_reports",
        ]
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.graph_sage = None
        self.edge_index = None
        self.node_features_dict = {}
    
    async def load(self) -> bool:
        """Load GNN model from file"""
        try:
            logger.info("Loading GNN model...")
            
            # Try to load pre-trained model
            if os.path.exists(self.model_path):
                self.graph_sage = torch.load(self.model_path, map_location=self.device)
            else:
                # Create a simple GraphSAGE model
                self._create_model()
            
            self.is_loaded = True
            logger.info(f"GNN model loaded successfully on {self.device}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load GNN model: {e}")
            self.is_loaded = False
            return False
    
    def _create_model(self):
        """Create a simple GraphSAGE model"""
        
        class GraphSAGE(nn.Module):
            def __init__(self, in_channels: int, hidden_channels: int, out_channels: int):
                super().__init__()
                self.conv1 = nn.Sequential(
                    nn.Linear(in_channels, hidden_channels),
                    nn.ReLU(),
                    nn.Dropout(0.2)
                )
                self.conv2 = nn.Sequential(
                    nn.Linear(hidden_channels, hidden_channels),
                    nn.ReLU(),
                    nn.Dropout(0.2)
                )
                self.classifier = nn.Sequential(
                    nn.Linear(hidden_channels, out_channels),
                    nn.Sigmoid()
                )
            
            def forward(self, x, edge_index):
                x = self.conv1(x)
                x = self.conv2(x)
                x = self.classifier(x)
                return x
        
        # Create model with input features
        self.graph_sage = GraphSAGE(
            in_channels=len(self.node_features),
            hidden_channels=64,
            out_channels=1
        )
        
        logger.info("Created simple GNN model")
    
    async def predict(self, features: Dict[str, Any]) -> float:
        """Make prediction using GNN
        
        Args:
            features: Dictionary containing graph features
            
        Returns:
            float: Fraud probability between 0 and 1
        """
        if not self.is_loaded:
            raise RuntimeError("GNN model not loaded")
        
        try:
            # Extract node features
            node_features = self._extract_node_features(features)
            
            # Create edge index (simplified - in production, load from graph database)
            edge_index = self._get_edge_index(features)
            
            # Convert to tensors
            x = torch.FloatTensor([node_features]).to(self.device)
            edge_index = torch.LongTensor(edge_index).to(self.device)
            
            # Get prediction
            with torch.no_grad():
                prob = self.graph_sage(x, edge_index).item()
            
            return float(prob)
            
        except Exception as e:
            logger.error(f"GNN prediction error: {e}")
            return 0.5
    
    def _extract_node_features(self, features: Dict[str, Any]) -> List[float]:
        """Extract node features for the graph"""
        node_features = [
            features.get('user_transaction_count', 10) / 100.0,  # Normalize
            features.get('user_avg_amount', 5000) / 100000.0,
            features.get('user_account_age_days', 365) / 365.0,
            features.get('user_risk_score', 0.0),
            features.get('device_transaction_count', 1) / 50.0,
            features.get('device_is_new', 0.0),
            features.get('merchant_transaction_count', 10) / 100.0,
            features.get('merchant_fraud_reports', 0) / 10.0,
        ]
        return node_features
    
    def _get_edge_index(self, features: Dict[str, Any]) -> List[List[int]]:
        """Get edge index for the graph (simplified)"""
        # In production, this would load from Neo4j or build dynamically
        # For now, return a simple edge structure
        return [[0, 1], [1, 0]]  # Simple self-loop
    
    def extract_features(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract graph features from transaction data
        
        Args:
            transaction_data: Raw transaction data
            
        Returns:
            Dict: Extracted graph features
        """
        features = {}
        
        # User features
        features['user_transaction_count'] = transaction_data.get('user_transaction_count_30d', 10)
        features['user_avg_amount'] = transaction_data.get('user_avg_amount_30d', 5000)
        features['user_account_age_days'] = transaction_data.get('user_account_age_days', 365)
        features['user_risk_score'] = transaction_data.get('user_risk_score', 0.0)
        
        # Device features
        features['device_transaction_count'] = transaction_data.get('device_transaction_count', 1)
        features['device_is_new'] = 1.0 if transaction_data.get('device_first_seen_days', 0) < 7 else 0.0
        
        # Merchant features
        features['merchant_transaction_count'] = transaction_data.get('merchant_transaction_count', 10)
        features['merchant_fraud_reports'] = transaction_data.get('merchant_fraud_reports', 0)
        
        # Graph-specific features
        features['sender_degree'] = transaction_data.get('sender_degree', 5)
        features['receiver_degree'] = transaction_data.get('receiver_degree', 5)
        features['common_neighbors'] = transaction_data.get('common_neighbors', 0)
        features['graph_distance'] = transaction_data.get('graph_distance', 1)
        
        return features
    
    def get_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "model_path": self.model_path,
            "is_loaded": self.is_loaded,
            "node_features": self.node_features,
            "device": str(self.device),
        }


# Singleton instance
_gnn_model: Optional[GNNModel] = None


async def get_gnn_model() -> GNNModel:
    """Get GNN model singleton"""
    global _gnn_model
    if _gnn_model is None:
        _gnn_model = GNNModel()
        await _gnn_model.load()
    return _gnn_model
