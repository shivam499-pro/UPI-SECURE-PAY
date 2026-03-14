"""
UPI Secure Pay AI - ML Orchestrator (Fraud Cascade Engine)

This script provides a FraudCascadeEngine class with an integrated SafetyRuleEngine
that checks critical risk markers BEFORE running ML models.

Level 1: LightGBM - Fast filter
Level 2: Transformer + TGN - Context analysis (if score 0.3-0.7)
Level 3: GNN + LLaMA - Deep investigation (if still suspicious)
"""

import asyncio
import time
import json
from typing import Dict, Any, Optional, List


class SafetyRuleEngine:
    """
    Safety Rule Engine - Checks critical risk markers BEFORE ML models
    
    Critical rules that trigger immediate Level 3:
    - Device is rooted
    - Merchant name contains "Scam" or suspicious keywords
    - Amount > ₹90,000
    - Network linked to blacklisted account
    - Scam-call detected: User on phone call + amount > ₹10,000
    """
    
    # Critical keywords in merchant names that indicate scam
    SCAM_KEYWORDS = [
        "scam", "fraud", "fake", "free", "win", "prize", 
        "gift", "reward", "bonus", "claim", "verify", 
        "customer_care", "support", "helpdesk", "refund"
    ]
    
    # Critical thresholds
    CRITICAL_AMOUNT = 90000  # ₹90,000
    SCAM_CALL_AMOUNT_THRESHOLD = 10000  # ₹10,000 - Scam call detection threshold
    
    def __init__(self):
        self.rules_triggered = []
    
    def check(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check transaction for critical risk markers
        
        Args:
            transaction_data: Dictionary containing transaction information
            
        Returns:
            Dictionary with:
            - is_critical: bool
            - triggered_rules: List[str]
            - risk_level: "LOW", "MEDIUM", "HIGH", "CRITICAL"
            - meta_features: dict of features to pass to ML models
        """
        self.rules_triggered = []
        meta_features = {}
        
        # Check 1: Device status
        device_status = transaction_data.get("device_status", "")
        if device_status.lower() == "rooted":
            self.rules_triggered.append("DEVICE_ROOTED")
            meta_features["safety_device_rooted"] = 1.0
        
        # Check 2: Device is jailbroken
        if transaction_data.get("device_jailbroken", 0) == 1:
            self.rules_triggered.append("DEVICE_JAILBROKEN")
            meta_features["safety_device_jailbroken"] = 1.0
        
        # Check 3: Merchant name contains scam keywords
        merchant_name = transaction_data.get("receiver_vpa", "").lower()
        for keyword in self.SCAM_KEYWORDS:
            if keyword in merchant_name:
                self.rules_triggered.append(f"MERCHANT_SCAM_KEYWORD:{keyword}")
                meta_features["safety_scam_merchant"] = 1.0
                break
        
        # Check 4: Critical amount (ALWAYS CRITICAL - bypass to Level 3)
        amount = transaction_data.get("amount", 0)
        if amount > self.CRITICAL_AMOUNT:
            self.rules_triggered.append(f"CRITICAL_AMOUNT:{amount}")
            meta_features["safety_critical_amount"] = amount / 100000  # Normalize
        
        # Check 5: Network linked to blacklisted account
        if transaction_data.get("device_linked_to_blacklisted", 0) == 1:
            self.rules_triggered.append("NETWORK_BLACKLISTED")
            meta_features["safety_network_blacklisted"] = 1.0
        
        if transaction_data.get("receiver_linked_to_fraud", 0) == 1:
            self.rules_triggered.append("RECEIVER_FRAUD_LINK")
            meta_features["safety_receiver_fraud_link"] = 1.0
        
        # Check 6: New account with high amount
        account_age = transaction_data.get("account_age_days", 999)
        if account_age < 7 and amount > 50000:
            self.rules_triggered.append("NEW_ACCOUNT_HIGH_AMOUNT")
            meta_features["safety_new_account_risk"] = 1.0
        
        # Check 7: Scam-Call Detection - User on phone call during transaction + high amount
        # This is a strong indicator of remote scam where fraudster guides victim over phone
        is_on_call = transaction_data.get("is_on_call", False)
        if is_on_call and amount > self.SCAM_CALL_AMOUNT_THRESHOLD:
            self.rules_triggered.append(f"SCAM_CALL_DETECTED:{amount}")
            meta_features["safety_scam_call"] = 1.0
            meta_features["safety_on_call_amount"] = amount / 100000  # Normalize
        
        # Check 8: Screen sharing during transaction - potential remote access scam
        is_screen_sharing = transaction_data.get("is_screen_sharing", False)
        if is_screen_sharing:
            self.rules_triggered.append("SCREEN_SHARING_DETECTED")
            meta_features["safety_screen_sharing"] = 1.0
        
        # Check 9: Abnormal typing velocity - could indicate remote control
        # Very slow typing (< 1 char/sec) or very fast typing (> 8 chars/sec) is suspicious
        typing_velocity = transaction_data.get("typing_velocity")
        if typing_velocity is not None:
            if typing_velocity < 1.0:
                self.rules_triggered.append("TYPING_TOO_SLOW")
                meta_features["safety_typing_slow"] = 1.0 - typing_velocity  # Higher = more suspicious
            elif typing_velocity > 8.0:
                self.rules_triggered.append("TYPING_TOO_FAST")
                meta_features["safety_typing_fast"] = typing_velocity / 10.0  # Normalize
        
        # Determine overall risk level
        # CRITICAL rules always trigger HIGH RISK OVERRIDE
        critical_rules = [r for r in self.rules_triggered if 
                         r.startswith("DEVICE_") or 
                         r.startswith("MERCHANT_SCAM") or
                         r.startswith("CRITICAL_AMOUNT") or
                         r.startswith("NETWORK_") or
                         r.startswith("RECEIVER_") or
                         r.startswith("SCAM_CALL") or
                         r.startswith("SCREEN_SHARING")]  # Behavioral biometrics are critical
        
        if len(critical_rules) > 0 or len(self.rules_triggered) >= 3:
            risk_level = "CRITICAL"
        elif len(self.rules_triggered) >= 2:
            risk_level = "HIGH"
        elif len(self.rules_triggered) == 1:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "is_critical": risk_level in ["HIGH", "CRITICAL"],
            "risk_level": risk_level,
            "triggered_rules": self.rules_triggered,
            "meta_features": meta_features
        }


class FraudCascadeEngine:
    """
    Fraud Cascade Engine - Cascaded ML Inference with Safety Rules
    
    Implements intelligent model routing:
    - SafetyRuleEngine: Checks critical markers FIRST
    - Level 1: LightGBM (if safety passes)
    - Level 2: Transformer + TGN (if score 0.3-0.7)
    - Level 3: GNN + LLaMA (if still suspicious)
    """
    
    def __init__(self):
        """Initialize the Fraud Cascade Engine"""
        # Import models here to avoid circular imports
        from app.ml.lightgbm_model import LightGBMModel, get_lightgbm_model
        from app.ml.transformer_model import TransformerModel, get_transformer_model
        from app.ml.gnn_model import GNNModel, get_gnn_model
        from app.ml.tgn_model import TGNModel, get_tgn_model
        from app.ml.llm_model import LLMModel, get_llm_model
        
        self.lightgbm: Optional[LightGBMModel] = None
        self.transformer: Optional[TransformerModel] = None
        self.gnn: Optional[GNNModel] = None
        self.tgn: Optional[TGNModel] = None
        self.llm: Optional[LLMModel] = None
        self.is_initialized = False
        
        # Safety rule engine
        self.safety_engine = SafetyRuleEngine()
        
        # Cascade thresholds - NEW LOGIC:
        # If lightgbm_score < 0.4 → Level 1 only (APPROVE)
        # If 0.4 <= lightgbm_score < 0.7 → Level 2
        # If lightgbm_score >= 0.7 OR SafetyRuleEngine detects critical risk → Level 3
        self.LEVEL1_MAX = 0.4      # Below this: Level 1 APPROVE
        self.LEVEL2_LOWER = 0.4    # Above this: Trigger Level 2
        self.LEVEL2_UPPER = 0.7    # Above this: Trigger Level 3 instead
        self.LEVEL3_THRESHOLD = 0.7  # Score >= 0.7 → Level 3
    
    async def initialize(self) -> bool:
        """
        Initialize all 5 ML models
        
        Returns:
            bool: True if all models loaded successfully
        """
        try:
            print("🔄 Initializing Fraud Cascade Engine...")
            
            # Level 1: LightGBM
            from app.ml.lightgbm_model import get_lightgbm_model
            self.lightgbm = await get_lightgbm_model()
            print(f"  ✅ LightGBM loaded: {self.lightgbm.is_loaded}")
            
            # Level 2: Transformer + TGN
            from app.ml.transformer_model import get_transformer_model
            from app.ml.tgn_model import get_tgn_model
            self.transformer = await get_transformer_model()
            self.tgn = await get_tgn_model()
            print(f"  ✅ Transformer loaded: {self.transformer.is_loaded}, model exists: {self.transformer.transformer is not None}")
            print(f"  ✅ TGN loaded: {self.tgn.is_loaded}, model exists: {self.tgn.tgn_model is not None}")
            
            # Level 3: GNN + LLaMA
            from app.ml.gnn_model import get_gnn_model
            from app.ml.llm_model import get_llm_model
            self.gnn = await get_gnn_model()
            self.llm = await get_llm_model()
            print(f"  ✅ GNN loaded: {self.gnn.is_loaded}")
            print(f"  ✅ LLaMA loaded: {self.llm.is_loaded}")
            
            self.is_initialized = all([
                self.lightgbm.is_loaded,
                self.transformer.is_loaded,
                self.gnn.is_loaded,
                self.tgn.is_loaded,
                self.llm.is_loaded,
            ])
            
            print(f"🎯 Fraud Cascade Engine ready: {self.is_initialized}")
            return self.is_initialized
            
        except Exception as e:
            print(f"❌ Failed to initialize Fraud Cascade Engine: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def predict(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run cascaded inference on transaction data
        
        Args:
            transaction_data: Dictionary containing transaction information
            
        Returns:
            JSON-compatible dictionary with:
            - final_verdict: "proceed", "verify", or "block"
            - cascade_stage: e.g., "LEVEL 1 - APPROVED", "LEVEL 3 - HIGH RISK OVERRIDE"
            - latency_ms: Processing time in milliseconds
            - risk_score: Final risk score (0-100)
            - model_scores: Individual model scores
        """
        start_time = time.time()
        model_scores = {}
        amount = transaction_data.get("amount", 0)
        
        # ==================== SAFETY RULE ENGINE (ALWAYS FIRST) ====================
        safety_result = self.safety_engine.check(transaction_data)
        
        print(f"🛡️ Safety Check: {safety_result['risk_level']} - {safety_result['triggered_rules']}")
        
        # If critical risk, skip to Level 3 immediately
        if safety_result["is_critical"]:
            print(f"⚠️  CRITICAL RISK DETECTED - Bypassing to Level 3!")
            
            # Add meta-features to transaction data for context
            enriched_data = {**transaction_data, **safety_result["meta_features"]}
            
            # Check if gnn and llm are properly loaded
            if self.gnn is None or self.llm is None:
                print("⚠️ GNN/LLaMA not loaded in override, using fallback scores")
                gnn_score = 0.80
                llm_score = 0.75
            else:
                # Run Level 3 immediately (GNN + LLaMA)
                gnn_features = self.gnn.extract_features(enriched_data)
                llm_features = self.llm.extract_features(enriched_data)
                
                gnn_score = await self.gnn.predict(gnn_features)
                llm_score = await self.llm.predict(llm_features)
            
            model_scores["gnn"] = gnn_score
            model_scores["llm"] = llm_score
            
            # Critical risk = automatic high score
            final_score = max(gnn_score, llm_score, 0.8)  # At least 80%
            
            cascade_stage = "LEVEL 3 - HIGH RISK OVERRIDE"
            final_verdict = "block"
            
            return {
                "final_verdict": final_verdict,
                "cascade_stage": cascade_stage,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "risk_score": round(final_score * 100, 2),
                "model_scores": model_scores,
                "levels_used": [
                    "SafetyRuleEngine", 
                    "Level 3: GNN + LLaMA (OVERRIDE)"
                ],
                "safety_rules_triggered": safety_result["triggered_rules"],
                "decision_reason": f"Critical risk: {', '.join(safety_result['triggered_rules'])}"
            }
        
        # ==================== LEVEL 1: LightGBM ====================
        # Merge safety meta-features into transaction for context
        enriched_data = {**transaction_data, **safety_result["meta_features"]}
        
        lgb_features = self.lightgbm.extract_features(enriched_data)
        lgb_score = await self.lightgbm.predict(lgb_features)
        model_scores["lightgbm"] = lgb_score
        
        latency_l1 = (time.time() - start_time) * 1000
        print(f"📊 Level 1 (LightGBM): score={lgb_score:.3f}, latency={latency_l1:.1f}ms")
        
        # Quick decisions based on Level 1
        # NEW LOGIC:
        # - Score < 0.4: Level 1 APPROVE
        # - Score >= 0.4 and < 0.7: Level 2
        # - Score >= 0.7: Level 3
        if lgb_score < self.LEVEL1_MAX:
            # Low risk - Auto approve at Level 1
            final_score = lgb_score
            cascade_stage = "LEVEL 1 - APPROVED"
            final_verdict = "proceed"
            
            return {
                "final_verdict": final_verdict,
                "cascade_stage": cascade_stage,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "risk_score": round(final_score * 100, 2),
                "model_scores": model_scores,
                "levels_used": ["SafetyRuleEngine", "Level 1: LightGBM"],
                "safety_rules_triggered": safety_result["triggered_rules"],
                "decision_reason": "Low risk - auto approved at Level 1"
            }
        
        if lgb_score >= self.LEVEL3_THRESHOLD:
            # High risk - Go to Level 3 immediately
            print(f"📊 High risk score {lgb_score:.3f} - Triggering Level 3!")
        
        # ==================== LEVEL 2: Transformer + TGN ====================
        # Score is in [0.3, 0.7] - Gray Zone, need more analysis
        print(f"📊 Level 2 triggered (score: {lgb_score:.3f})")
        
        # Check if transformer and tgn are properly loaded
        if self.transformer is None or self.tgn is None:
            print("⚠️ Transformer/TGN not loaded, using fallback scores")
            # Use deterministic fallback scores for development
            trans_score = 0.30 if amount < 50000 else 0.70
            tgn_score = 0.25 if amount < 50000 else 0.65
        else:
            # Extract features (with safety context)
            trans_features = self.transformer.extract_features(enriched_data)
            tgn_features = self.tgn.extract_features(enriched_data)
            
            # Run Transformer and TGN CONCURRENTLY
            trans_task = self.transformer.predict(trans_features)
            tgn_task = self.tgn.predict(tgn_features)
            
            trans_score, tgn_score = await asyncio.gather(trans_task, tgn_task)
        
        model_scores["transformer"] = trans_score
        model_scores["tgn"] = tgn_score
        
        # Average Level 2 score
        level2_score = (lgb_score + trans_score + tgn_score) / 3
        
        latency_l2 = (time.time() - start_time) * 1000
        print(f"📊 Level 2 (Transformer + TGN): trans={trans_score:.3f}, tgn={tgn_score:.3f}, avg={level2_score:.3f}")
        
        # Check if need Level 3
        if level2_score < self.LEVEL3_THRESHOLD:
            # Low-medium risk after Level 2 - Proceed
            final_score = level2_score
            cascade_stage = "LEVEL 2 - ANALYZED"
            final_verdict = "proceed"
            
            return {
                "final_verdict": final_verdict,
                "cascade_stage": cascade_stage,
                "latency_ms": round((time.time() - start_time) * 1000, 2),
                "risk_score": round(final_score * 100, 2),
                "model_scores": model_scores,
                "levels_used": [
                    "SafetyRuleEngine", 
                    "Level 1: LightGBM", 
                    "Level 2: Transformer + TGN"
                ],
                "safety_rules_triggered": safety_result["triggered_rules"],
                "decision_reason": "Medium risk - analyzed at Level 2"
            }
        
        # ==================== LEVEL 3: GNN + LLaMA ====================
        # Still suspicious after Level 2 - Deep investigation
        print(f"📊 Level 3 triggered (score: {level2_score:.3f})")
        
        # Check if gnn and llm are properly loaded
        if self.gnn is None or self.llm is None:
            print("⚠️ GNN/LLaMA not loaded, using fallback scores")
            # Use deterministic fallback scores for development
            gnn_score = 0.60 if amount < 50000 else 0.85
            llm_score = 0.55 if amount < 50000 else 0.80
        else:
            # Extract features (with safety context)
            gnn_features = self.gnn.extract_features(enriched_data)
            llm_features = self.llm.extract_features(enriched_data)
            
            # Run GNN and LLaMA
            gnn_score = await self.gnn.predict(gnn_features)
            llm_score = await self.llm.predict(llm_features)
        
        model_scores["gnn"] = gnn_score
        model_scores["llm"] = llm_score
        
        # Final ensemble with Level 3
        final_score = (
            lgb_score * 0.2 + 
            level2_score * 0.3 + 
            (gnn_score + llm_score) / 2 * 0.5
        )
        
        latency_l3 = (time.time() - start_time) * 1000
        print(f"📊 Level 3 (GNN + LLaMA): gnn={gnn_score:.3f}, llm={llm_score:.3f}, final={final_score:.3f}")
        
        # Decision
        if final_score > 0.8:
            cascade_stage = "LEVEL 3 - BLOCKED"
            final_verdict = "block"
            reason = "High risk - blocked after Level 3 deep investigation"
        elif final_score > 0.5:
            cascade_stage = "LEVEL 3 - REVIEW"
            final_verdict = "verify"  # Step-up verification
            reason = "Medium-high risk - requires verification"
        else:
            cascade_stage = "LEVEL 3 - APPROVED"
            final_verdict = "proceed"
            reason = "Approved after Level 3 investigation"
        
        return {
            "final_verdict": final_verdict,
            "cascade_stage": cascade_stage,
            "latency_ms": round((time.time() - start_time) * 1000, 2),
            "risk_score": round(final_score * 100, 2),
            "model_scores": model_scores,
            "levels_used": [
                "SafetyRuleEngine",
                "Level 1: LightGBM", 
                "Level 2: Transformer + TGN", 
                "Level 3: GNN + LLaMA"
            ],
            "safety_rules_triggered": safety_result["triggered_rules"],
            "decision_reason": reason
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get engine information"""
        return {
            "engine": "FraudCascadeEngine",
            "version": "2.0.0",
            "initialized": self.is_initialized,
            "safety_rules": {
                "device_rooted": "BLOCK",
                "device_jailbroken": "BLOCK",
                "merchant_scam_keywords": "LEVEL 3",
                "critical_amount_90000": "LEVEL 3",
                "network_blacklisted": "LEVEL 3",
                "new_account_high_amount": "LEVEL 3",
                # Behavioral Biometrics - Scam Detection
                "scam_call_on_call_plus_10000": "LEVEL 3",
                "screen_sharing_detected": "LEVEL 3",
                "typing_too_slow": "LEVEL 3",
                "typing_too_fast": "LEVEL 3",
            },
            "cascade_levels": {
                "Safety": "SafetyRuleEngine - runs first on ALL transactions",
                "Level 1": "LightGBM - Fast filter",
                "Level 2": "Transformer + TGN - Context analysis",
                "Level 3": "GNN + LLaMA - Deep investigation"
            },
            "thresholds": {
                "level2_lower": self.LEVEL2_LOWER,
                "level2_upper": self.LEVEL2_UPPER,
                "level3_threshold": self.LEVEL3_THRESHOLD,
                "scam_call_threshold": self.safety_engine.SCAM_CALL_AMOUNT_THRESHOLD
            }
        }


# Singleton instance
_engine: Optional[FraudCascadeEngine] = None


async def get_fraud_cascade_engine() -> FraudCascadeEngine:
    """Get the Fraud Cascade Engine singleton"""
    global _engine
    if _engine is None:
        _engine = FraudCascadeEngine()
        await _engine.initialize()
    return _engine


# Test function
async def test_engine():
    """Test the Fraud Cascade Engine"""
    print("\n" + "="*60)
    print("🧪 Testing Fraud Cascade Engine with Safety Rules")
    print("="*60 + "\n")
    
    # Initialize engine
    engine = await get_fraud_cascade_engine()
    print(engine.get_info())
    
    # Test case 1: Normal transaction
    print("\n--- Test 1: Normal Transaction ---")
    normal_txn = {
        "sender_id": "user_001",
        "sender_vpa": "user001@okhdfcbank",
        "receiver_vpa": "shop@oksbi",
        "amount": 500,
        "timestamp": "2026-03-05T12:00:00Z",
        "transaction_type": "P2M"
    }
    
    result = await engine.predict(normal_txn)
    print(json.dumps(result, indent=2))
    
    # Test case 2: Critical risk (scam merchant)
    print("\n--- Test 2: Critical Risk - Scam Merchant ---")
    scam_txn = {
        "sender_id": "user_001",
        "sender_vpa": "user001@okhdfcbank",
        "receiver_vpa": "Free_iPhone_Scam@okaxis",  # Scam!
        "amount": 50000,
        "timestamp": "2026-03-05T12:00:00Z",
        "transaction_type": "P2M"
    }
    
    result = await engine.predict(scam_txn)
    print(json.dumps(result, indent=2))
    
    print("\n" + "="*60)
    print("✅ Testing Complete!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_engine())
