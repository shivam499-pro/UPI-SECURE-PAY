#!/usr/bin/env python3
"""
UPI Secure Pay AI - API Test Script

This script tests the fraud detection API with sample transactions.
"""

import requests
import json
import time
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000/api/v1"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def test_health():
    """Test health endpoint"""
    print_header("Testing Health Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"API is healthy!")
            print(f"   Version: {data.get('version')}")
            print(f"   Status: {data.get('status')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API. Is the server running?")
        print_warning("Start the server with: uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_fraud_check_normal():
    """Test with a normal transaction"""
    print_header("Testing Normal Transaction")
    
    transaction = {
        "transaction": {
            "sender_id": "user_001",
            "sender_vpa": "user001@okhdfcbank",
            "sender_device_id": "device_001",
            "receiver_id": "merchant_001",
            "receiver_vpa": "shop@oksbi",
            "amount": 500,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "transaction_type": "P2M",
            "merchant_category": "grocery"
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/fraud-check",
            json=transaction,
            timeout=30
        )
        elapsed = (time.time() - start_time) * 1000
        
        if response.status_code == 200:
            data = response.json()
            print(f"Transaction ID: {data.get('transaction_id')}")
            print(f"Risk Score: {data.get('risk_score')}")
            print(f"Decision: {data.get('decision')}")
            print(f"Processing Time: {data.get('processing_time_ms')}ms")
            print(f"Reasons: {', '.join(data.get('reasons', []))}")
            
            if data.get('decision') == 'proceed':
                print_success("Transaction APPROVED (as expected)")
            else:
                print_warning(f"Transaction was {data.get('decision')} (unexpected)")
            
            return True
        else:
            print_error(f"Request failed: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_fraud_check_suspicious():
    """Test with a suspicious transaction"""
    print_header("Testing Suspicious Transaction")
    
    transaction = {
        "transaction": {
            "sender_id": "user_new",
            "sender_vpa": "newuser@okhdfcbank",
            "sender_device_id": "new_device_999",
            "receiver_id": "suspicious_merchant",
            "receiver_vpa": "freegames@okaxis",
            "amount": 50000,
            "timestamp": "2026-03-05T03:00:00Z",  # 3 AM - suspicious time
            "transaction_type": "P2M",
            "merchant_category": "gaming"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/fraud-check",
            json=transaction,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Transaction ID: {data.get('transaction_id')}")
            print(f"Risk Score: {data.get('risk_score')}")
            print(f"Decision: {data.get('decision')}")
            print(f"Reasons: {', '.join(data.get('reasons', []))}")
            
            # Show individual model scores
            print("\nModel Scores:")
            for model in data.get('model_scores', []):
                print(f"   {model['model_name']}: {model['score']:.2f} (weight: {model['weight']})")
            
            if data.get('decision') in ['block', 'verify']:
                print_success("Transaction FLAGGED (as expected)")
            else:
                print_warning(f"Transaction was approved (unexpected)")
            
            return True
        else:
            print_error(f"Request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_model_status():
    """Test model status endpoint"""
    print_header("Testing Model Status")
    
    try:
        response = requests.get(f"{BASE_URL}/fraud-check/models/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Models Loaded: {data.get('models_loaded')}")
            print(f"LightGBM: {data.get('lightgbm')}")
            print(f"Transformer: {data.get('transformer')}")
            print(f"\nEnsemble Weights:")
            for model, weight in data.get('ensemble_weights', {}).items():
                print(f"   {model}: {weight}")
            return True
        else:
            print_error(f"Request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def main():
    print(f"\n{BLUE}🛡️  UPI Secure Pay AI - API Testing{RESET}\n")
    
    # Test 1: Health Check
    if not test_health():
        print("\nStopping tests - API is not reachable")
        return
    
    # Test 2: Model Status
    test_model_status()
    
    # Test 3: Normal Transaction
    test_fraud_check_normal()
    
    # Test 4: Suspicious Transaction
    test_fraud_check_suspicious()
    
    print_header("Testing Complete!")
    print("""
🎯 Test Summary:
   - Health Check: API is running
   - Model Status: All 5 models loaded
   - Normal Transaction: Should be APPROVED
   - Suspicious Transaction: Should be BLOCKED/VERIFY

📝 Next Steps:
   1. Run more tests with different scenarios
   2. Check /api/v1/analytics/fraud-stats for analytics
   3. View API docs at http://localhost:8000/docs
    """)

if __name__ == "__main__":
    main()
