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
    # Specifically target the path inside the 'backend' folder
    from backend.app.ml_orchestrator import get_fraud_cascade_engine
    
    engine = await get_fraud_cascade_engine()
    result = await engine.predict(transaction_data)
    return result


def main():
    """Main dashboard function"""
    init_session_state()
    
    # Header
    st.title("🛡️ UPI Secure Pay AI")
    st.title("Fraud Detection Cascade Engine")
    
    st.markdown("---")
    
    # Sidebar with inputs
    st.sidebar.header("📝 Transaction Details")

    # Analyze Button
    if st.sidebar.button("🔍 Analyze Transaction", type="primary", use_container_width=True):
        with st.spinner("Running Fraud Cascade..."):
            result = asyncio.run(analyze_transaction(transaction_data))
            st.session_state.result = result
    
    # Display results
    if st.session_state.result:
        result = st.session_state.result
        
        # 1. Status Banner
        verdict = result.get("final_verdict", "unknown")
        stage = result.get("cascade_stage", "UNKNOWN")
        
        if verdict == "proceed":
            st.success(f"### ✅ APPROVED ({stage})")
        elif verdict == "verify":
            st.warning(f"### ⚠️ REVIEW NEEDED ({stage})")
        else:
            st.error(f"### 🚫 BLOCKED ({stage})")
        
        # 2. Risk Metrics
        col1, col2 = st.columns(2)
        col1.metric("Risk Score", f"{result.get('risk_score', 0):.1f}%")
        col2.metric("Latency", f"{result.get('latency_ms', 0)}ms")

        # 3. FIX: Define rules FIRST
        rules = result.get("safety_rules_triggered", [])
        
        # 4. Behavioral Biometrics Alert
        behavioral_rules = [r for r in rules if any(x in r for x in ["SCAM_", "SCREEN_", "TYPING"])]
        if behavioral_rules:
            st.warning(f"🚨 **Behavioral Biometrics Alert:** {', '.join(behavioral_rules)}")
        
        # 5. Safety rules triggered
        if rules:
            st.warning(f"🛡️ **Safety Rules Triggered:** {', '.join(rules)}")
        
        # ... [Keep your Model Breakdown Table code here] ...

        # 6. LLaMA Reasoning Section (Corrected)
        st.markdown("### 🧠 AI Reasoning & Explanation")
        llm_reasoning = result.get("llm_reasoning")
        if llm_reasoning:
            st.info(llm_reasoning)
        else:
            st.info("No AI reasoning available for this transaction.")
    
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
    
    # Behavioral Biometrics - Scam Detection
    st.sidebar.markdown("--- Behavioral Biometrics ---")
    
    is_on_call = st.sidebar.checkbox(
        "📞 User is on Phone Call",
        value=False,
        help="Check if user is currently on a call (potential scam indicator)"
    )
    
    is_screen_sharing = st.sidebar.checkbox(
        "🖥️ Screen Sharing Active",
        value=False,
        help="Check if user is sharing their screen (potential remote scam)"
    )
    
    typing_velocity = st.sidebar.slider(
        "⌨️ Typing Velocity (chars/sec)",
        min_value=0.0,
        max_value=10.0,
        value=4.0,
        step=0.5,
        help="Normal typing is 2-6 chars/sec. Very slow (<1) or very fast (>8) is suspicious"
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
        # Behavioral Biometrics
        "is_on_call": is_on_call,
        "is_screen_sharing": is_screen_sharing,
        "typing_velocity": typing_velocity,
    }
    
    # Analyze Button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔍 Analyze Transaction", type="primary", use_container_width=True, key="analyze_transaction_btn"):
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
        
        # 3. GET RULES FIRST (Fixes the crash)
        rules = result.get("safety_rules_triggered", [])
        
        # 4. Behavioral Biometrics Analysis
        behavioral_rules = [r for r in rules if any(x in r for x in ["SCAM_", "SCREEN_", "TYPING"])]
        if behavioral_rules:
            st.warning(f"🚨 **Behavioral Biometrics Alert:** {', '.join(behavioral_rules)}")
        
        # 5. Safety rules triggered
        if rules:
            st.warning(f"🛡️ **Safety Rules Triggered:** {', '.join(rules)}")
        
        # 6. Decision reason
        reason = result.get("decision_reason", "")
        if reason:
            st.info(f"💡 **Decision Logic:** {reason}")
        
        # 7. LLaMA Reasoning Section
        st.markdown("### 🧠 AI Reasoning & Explanation")
        llm_reasoning = result.get("llm_reasoning", "")
        if llm_reasoning:
            st.markdown(f"<div style='background-color: #e8f4fd; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3;'>{llm_reasoning}</div>", unsafe_allow_html=True)
        elif "Level 3" in stage:
            # Fallback logic for when LLaMA isn't explicitly returned
            st.info("High-risk transaction deep-dived by GNN and Pattern Analysis.")
            # Generate reasoning based on the analysis
            reasoning_parts = []
            if rules:
                reasoning_parts.append(f"Safety rules triggered: {', '.join(rules)}")
            scores = result.get("model_scores", {})
            if scores.get("gnn", 0) > 0.5:
                reasoning_parts.append(f"Graph analysis detected suspicious network patterns (GNN score: {scores.get('gnn', 0)*100:.1f}%)")
            if scores.get("llm", 0) > 0.5:
                reasoning_parts.append(f"AI analysis flagged unusual transaction behavior (LLaMA score: {scores.get('llm', 0)*100:.1f}%)")
            
            if reasoning_parts:
                st.markdown("### 🧠 Reasoning (AI Explanation)")
                st.markdown(f"<div style='background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #6366f1;'>{'. '.join(reasoning_parts)}</div>", unsafe_allow_html=True)
        
        # Latency
        latency = result.get("latency_ms", 0)
        st.caption(f"⏱️ Processing Time: {latency}ms")


if __name__ == "__main__":
    main()
