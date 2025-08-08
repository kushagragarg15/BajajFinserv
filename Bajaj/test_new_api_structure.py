#!/usr/bin/env python3
"""
Test script to verify the new API structure works correctly
"""

import requests
import json

def test_new_api_structure():
    """Test the new API structure with /api/v1 prefix"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing New API Structure")
    print("=" * 50)
    
    # Test 1: Health check (should work)
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health endpoint works")
            health_data = response.json()
            print(f"   Status: {health_data.get('overall_status', 'unknown')}")
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
    
    # Test 2: Root endpoint
    print("\n2. Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✅ Root endpoint works")
            root_data = response.json()
            print(f"   Message: {root_data.get('message', 'unknown')}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
    
    # Test 3: New API endpoint structure
    print("\n3. Testing new API endpoint structure...")
    
    # Test the new endpoint path
    new_endpoint = f"{base_url}/api/v1/hackrx/run"
    
    request_data = {
        "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "questions": [
            "What is this document about?",
            "What are the main points?"
        ]
    }
    
    headers = {
        "Authorization": "Bearer 04882ff997f04a7548a2640b6ac4ca31bb61a48594229f92000cc82b4e6dbd3d",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"   Making request to: {new_endpoint}")
        response = requests.post(
            new_endpoint,
            json=request_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ New API endpoint works!")
            result = response.json()
            print(f"   Received {len(result.get('answers', []))} answers")
            print(f"   First answer preview: {result.get('answers', [''])[0][:100]}...")
        elif response.status_code == 422:
            print("❌ 422 Error - Check request format")
            try:
                error_detail = response.json()
                print(f"   Error details: {error_detail}")
            except:
                print(f"   Raw error: {response.text}")
        else:
            print(f"❌ API endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ API endpoint error: {e}")
    
    # Test 4: Performance endpoint
    print("\n4. Testing performance endpoint...")
    try:
        response = requests.get(f"{base_url}/performance", timeout=5)
        if response.status_code == 200:
            print("✅ Performance endpoint works")
            perf_data = response.json()
            print(f"   Status: {perf_data.get('status', 'unknown')}")
        else:
            print(f"❌ Performance endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Performance endpoint error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 API Structure Summary:")
    print(f"   Base URL: {base_url}")
    print(f"   Health: {base_url}/health")
    print(f"   Root: {base_url}/")
    print(f"   Main API: {base_url}/api/v1/hackrx/run")
    print(f"   Performance: {base_url}/performance")
    print("=" * 50)

if __name__ == "__main__":
    test_new_api_structure()