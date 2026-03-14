"""
UPI Secure Pay AI - Full System Test

Tests all endpoints of the fraud detection system:
- Health check
- Normal transaction (should APPROVE)
- Suspicious transaction (should BLOCK/REVIEW)
- Batch processing
- Analytics endpoints
- Kafka status
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx


BASE_URL = "http://localhost:8000/api/v1"


def print_result(test_name: str, status_code: int, response: dict, expected: str):
    """Print test result"""
    if 200 <= status_code < 300:
        print(f"✅ PASS - {test_name}")
    else:
        print(f"❌ FAIL - {test_name}")
    print(f"   Status: {status_code}")
    print(f"   Expected: {expected}")
    print(f"   Response: {response}")
    print()
    return 200 <= status_code < 300


async def test_health_check():
    """Test 1: Health Check"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")
            data = response.json()
            return print_result("Health Check", response.status_code, data, "200 OK")
        except Exception as e:
            print(f"❌ FAIL - Health Check - Error: {e}")
            return False


async def test_normal_transaction():
    """Test 2: Normal Transaction (should APPROVE)"""
    print("\n" + "="*60)
    print("TEST 2: Normal Transaction (should APPROVE)")
    print("="*60)
    
    transaction = {
        "transaction": {
            "sender_id": "user_001",
            "sender_vpa": "user001@okhdfcbank",
            "sender_device_id": "device_001",
            "receiver_id": "merchant_001",
            "receiver_vpa": "grocery_store@oksbi",
            "amount": 500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_type": "P2M",
            "merchant_category": "grocery",
            "device_status": "normal",
            "is_on_call": False,
            "is_screen_sharing": False
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/fraud-check", json=transaction)
            data = response.json()
            
            # Check if approved
            is_approved = data.get("decision") == "proceed"
            if is_approved:
                print(f"✅ PASS - Normal Transaction")
            else:
                print(f"❌ FAIL - Normal Transaction - Expected 'proceed', got '{data.get('decision')}'")
            
            print(f"   Status: {response.status_code}")
            print(f"   Decision: {data.get('decision')}")
            print(f"   Risk Score: {data.get('risk_score')}")
            print(f"   Cascade Stage: {data.get('cascade_stage')}")
            print(f"   Response: {data}")
            print()
            return is_approved
            
        except Exception as e:
            print(f"❌ FAIL - Normal Transaction - Error: {e}")
            return False


async def test_suspicious_transaction():
    """Test 3: Suspicious Transaction (should BLOCK/REVIEW)"""
    print("\n" + "="*60)
    print("TEST 3: Suspicious Transaction (should BLOCK/REVIEW)")
    print("="*60)
    
    transaction = {
        "transaction": {
            "sender_id": "user_002",
            "sender_vpa": "user002@okhdfcbank",
            "sender_device_id": "device_002",
            "receiver_id": "scam_merchant",
            "receiver_vpa": "lottery winner scam@okaxis",
            "amount": 95000,  # Above ₹90,000 threshold
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transaction_type": "P2M",
            "merchant_category": "gaming",
            "device_status": "rooted",
            "is_on_call": True,  # Scam call detected
            "is_screen_sharing": False,
            "device_linked_to_blacklisted": 0,
            "receiver_linked_to_fraud": 0
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/fraud-check", json=transaction)
            data = response.json()
            
            # Check if blocked or review
            is_suspicious = data.get("decision") in ["block", "verify"]
            if is_suspicious:
                print(f"✅ PASS - Suspicious Transaction")
            else:
                print(f"❌ FAIL - Suspicious Transaction - Expected 'block' or 'verify', got '{data.get('decision')}'")
            
            print(f"   Status: {response.status_code}")
            print(f"   Decision: {data.get('decision')}")
            print(f"   Risk Score: {data.get('risk_score')}")
            print(f"   Cascade Stage: {data.get('cascade_stage')}")
            print(f"   Safety Rules: {data.get('safety_rules_triggered', [])}")
            print(f"   Response: {data}")
            print()
            return is_suspicious
            
        except Exception as e:
            print(f"❌ FAIL - Suspicious Transaction - Error: {e}")
            return False


async def test_batch_processing():
    """Test 4: Batch Processing"""
    print("\n" + "="*60)
    print("TEST 4: Batch Processing")
    print("="*60)
    
    batch_request = {
        "transactions": [
            {
                "sender_id": "user_001",
                "sender_vpa": "user001@okhdfcbank",
                "sender_device_id": "device_001",
                "receiver_id": "merchant_001",
                "receiver_vpa": "shop@oksbi",
                "amount": 500,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_type": "P2M"
            },
            {
                "sender_id": "user_002",
                "sender_vpa": "user002@okhdfcbank",
                "sender_device_id": "device_002",
                "receiver_id": "merchant_002",
                "receiver_vpa": "store@oksbi",
                "amount": 2000,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_type": "P2M"
            },
            {
                "sender_id": "user_003",
                "sender_vpa": "user003@okhdfcbank",
                "sender_device_id": "device_003",
                "receiver_id": "merchant_003",
                "receiver_vpa": "grocery@oksbi",
                "amount": 1000,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transaction_type": "P2M"
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{BASE_URL}/fraud-check/batch", json=batch_request)
            data = response.json()
            
            # Check if batch processed
            success = data.get("total_transactions") == 3
            if success:
                print(f"✅ PASS - Batch Processing")
            else:
                print(f"❌ FAIL - Batch Processing")
            
            print(f"   Status: {response.status_code}")
            print(f"   Total Transactions: {data.get('total_transactions')}")
            print(f"   Results Count: {len(data.get('results', []))}")
            print(f"   Response: {data}")
            print()
            return success
            
        except Exception as e:
            print(f"❌ FAIL - Batch Processing - Error: {e}")
            return False


async def test_analytics_fraud_stats():
    """Test 5: Analytics - Fraud Stats"""
    print("\n" + "="*60)
    print("TEST 5: Analytics - Fraud Stats")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/analytics/fraud-stats?time_range=7d")
            data = response.json()
            
            # Check if stats returned
            has_data = "total_transactions" in data
            if has_data:
                print(f"✅ PASS - Analytics Fraud Stats")
            else:
                print(f"❌ FAIL - Analytics Fraud Stats")
            
            print(f"   Status: {response.status_code}")
            print(f"   Total Transactions: {data.get('total_transactions')}")
            print(f"   Response: {data}")
            print()
            return has_data
            
        except Exception as e:
            print(f"❌ FAIL - Analytics Fraud Stats - Error: {e}")
            return False


async def test_analytics_model_performance():
    """Test 6: Analytics - Model Performance"""
    print("\n" + "="*60)
    print("TEST 6: Analytics - Model Performance")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/analytics/model-performance?time_range=7d")
            data = response.json()
            
            # Check if stats returned
            has_data = "cascade_usage" in data or "total_predictions" in data
            if has_data:
                print(f"✅ PASS - Analytics Model Performance")
            else:
                print(f"❌ FAIL - Analytics Model Performance")
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {data}")
            print()
            return has_data
            
        except Exception as e:
            print(f"❌ FAIL - Analytics Model Performance - Error: {e}")
            return False


async def test_kafka_status():
    """Test 7: Kafka Status"""
    print("\n" + "="*60)
    print("TEST 7: Kafka Status")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/kafka/status")
            data = response.json()
            
            # Check if status returned
            has_status = "consumer_running" in data
            if has_status:
                print(f"✅ PASS - Kafka Status")
            else:
                print(f"❌ FAIL - Kafka Status")
            
            print(f"   Status: {response.status_code}")
            print(f"   Consumer Running: {data.get('consumer_running')}")
            print(f"   Messages Processed: {data.get('messages_processed')}")
            print(f"   Kafka Available: {data.get('kafka_available')}")
            print(f"   Response: {data}")
            print()
            return has_status
            
        except Exception as e:
            print(f"❌ FAIL - Kafka Status - Error: {e}")
            return False


async def test_transactions_by_risk():
    """Test 8: Analytics - Transactions by Risk"""
    print("\n" + "="*60)
    print("TEST 8: Analytics - Transactions by Risk")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/analytics/transactions-by-risk?time_range=7d")
            data = response.json()
            
            # Check if stats returned
            has_data = "risk_distribution" in data
            if has_data:
                print(f"✅ PASS - Transactions by Risk")
            else:
                print(f"❌ FAIL - Transactions by Risk")
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {data}")
            print()
            return has_data
            
        except Exception as e:
            print(f"❌ FAIL - Transactions by Risk - Error: {e}")
            return False


async def test_top_merchants():
    """Test 9: Analytics - Top Merchants"""
    print("\n" + "="*60)
    print("TEST 9: Analytics - Top Merchants")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/analytics/top-merchants?limit=5&time_range=7d")
            data = response.json()
            
            # Check if stats returned
            has_data = "merchants" in data
            if has_data:
                print(f"✅ PASS - Top Merchants")
            else:
                print(f"❌ FAIL - Top Merchants")
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {data}")
            print()
            return has_data
            
        except Exception as e:
            print(f"❌ FAIL - Top Merchants - Error: {e}")
            return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("🛡️  UPI SECURE PAY AI - FULL SYSTEM TEST")
    print("="*70)
    
    results = []
    
    # Run tests
    results.append(("Health Check", await test_health_check()))
    results.append(("Normal Transaction", await test_normal_transaction()))
    results.append(("Suspicious Transaction", await test_suspicious_transaction()))
    results.append(("Batch Processing", await test_batch_processing()))
    results.append(("Analytics Fraud Stats", await test_analytics_fraud_stats()))
    results.append(("Analytics Model Performance", await test_analytics_model_performance()))
    results.append(("Transactions by Risk", await test_transactions_by_risk()))
    results.append(("Top Merchants", await test_top_merchants()))
    results.append(("Kafka Status", await test_kafka_status()))
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
    
    print("="*70)
    
    return passed == total


if __name__ == "__main__":
    # Check if server is running
    import socket
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8000))
    sock.close()
    
    if result != 0:
        print("❌ ERROR: Server is not running on localhost:8000")
        print("Please start the server first: uvicorn app.main:app")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
