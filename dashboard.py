"""
UPI Secure Pay AI - Fraud Monitoring Dashboard

A Streamlit-based dashboard for real-time fraud detection.
"""

import sys
import os

# Add backend to path for imports
sys.path.append('backend')

import streamlit as st
import asyncio
from datetime import datetime, timezone


# Page configuration
st.set_page_config(
    page_title="UPI Secure Pay AI - Fraud Detection",
    page_icon="🛡️",
    layout="centered"
)


def init_session_state():
    """Initialize session state"""
    if 'result' not in st.session_state:
        st.session_state.result = None


async def analyze_transaction(transaction_data):
    """Send transaction to fraud detection engine"""
    from app.ml_orchestrator import get_fraud_cascade_engine
    
    engine = await get_fraud_cascade_engine()
    result = await engine.predict(transaction_data)
    return result


def main():
    """Main dashboard function"""
    init_session_state()
    
    # Header
    st.title("🛡️ UPI Secure Pay AI")
    st.title("Fraud Detection Dashboard")
    
    st.markdown("---")
    
    # Sidebar with inputs
    st.sidebar.header("📝 Transaction Details")
    
    # Amount
    amount = st.sidebar.number_input(
        "Amount (₹)",
        min_value=1,
        max_value=10000000,
        value=500,
        step=100
    )
    
    # Merchant
    merchant = st.sidebar.text_input(
        "Merchant VPA",
        value="grocery_store@oksbi"
    )
    
    # Device Status
    device_status = st.sidebar.selectbox(
        "Device Status",
        ["normal", "rooted", "jailbroken"],
        index=0
    )
    
    # Build transaction data
    transaction_data = {
        "sender_id": "user001",
        "sender_vpa": "user001@okhdfcbank",
        "sender_device_id": "device_001",
        "receiver_id": merchant.split("@")[0] if "@" in merchant else merchant,
        "receiver_vpa": merchant,
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "transaction_type": "P2M",
        "merchant_category": "grocery",
        "device_status": device_status,
    }
    
    # Analyze Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 Analyze Transaction", type="primary", use_container_width=True):
        with st.spinner("Analyzing transaction..."):
            result = asyncio.run(analyze_transaction(transaction_data))
            st.session_state.result = result
    
    # Display results
    if st.session_state.result:
        result = st.session_state.result
        
        st.markdown("---")
        
        # Main verdict
        verdict = result.get("final_verdict", "unknown")
        stage = result.get("cascade_stage", "UNKNOWN")
        
        if verdict == "proceed":
            st.success(f"✅ APPROVED - {stage}")
        elif verdict == "verify":
            st.warning(f"⚠️ REVIEW NEEDED - {stage}")
        else:
            st.error(f"🚫 BLOCKED - {stage}")
        
        # Risk score
        risk_score = result.get("risk_score", 0)
        st.metric("Risk Score", f"{risk_score:.1f}%")
        
        # Model breakdown table
        st.markdown("### 📊 Model Breakdown")
        
        levels = result.get("levels_used", [])
        scores = result.get("model_scores", {})
        
        # Create a clean table
        table_data = []
        for level in levels:
            if "OVERRIDE" in level:
                table_data.append({"Level": level, "Status": "✅ Completed"})
            elif "Level 1" in level:
                score = scores.get("lightgbm", 0) * 100
                table_data.append({"Level": "Level 1: LightGBM", "Score": f"{score:.1f}%", "Status": "✅ Completed"})
            elif "Level 2" in level:
                t_score = scores.get("transformer", 0) * 100
                tg_score = scores.get("tgn", 0) * 100
                table_data.append({"Level": "Level 2: Transformer + TGN", "Score": f"Trans: {t_score:.1f}%, TGN: {tg_score:.1f}%", "Status": "✅ Completed"})
            elif "Level 3" in level:
                g_score = scores.get("gnn", 0) * 100
                l_score = scores.get("llm", 0) * 100
                table_data.append({"Level": "Level 3: GNN + LLaMA", "Score": f"GNN: {g_score:.1f}%, LLaMA: {l_score:.1f}%", "Status": "✅ Completed"})
            elif "Safety" in level:
                table_data.append({"Level": "SafetyRuleEngine", "Status": "✅ Completed"})
        
        # Display table
        if table_data:
            st.table(table_data)
        
        # Safety rules triggered
        rules = result.get("safety_rules_triggered", [])
        if rules:
            st.warning(f"🚨 Safety Rules Triggered: {', '.join(rules)}")
        
        # Decision reason
        reason = result.get("decision_reason", "")
        if reason:
            st.info(f"💡 {reason}")
        
        # Latency
        latency = result.get("latency_ms", 0)
        st.caption(f"⏱️ Processing Time: {latency}ms")


if __name__ == "__main__":
    main()
