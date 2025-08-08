#!/usr/bin/env python3
"""
Test script to show all available API endpoints
"""

import requests
import json

def test_all_endpoints():
    """Test all available endpoints to show the correct URLs"""
    
    base_url = "http://localhost:8000"
    
    print("🔍 Testing All Available Endpoints")
    print("=" * 60)
    
    endpoints_to_test = [
        {
            "name": "Root",
            "url": f"{base_url}/",
            "method": "GET",
            "description": "Main application root"
        },
        {
            "name": "Health Check",
            "url": f"{base_url}/health",
            "method": "GET", 
            "description": "Server health status"
        },
        {
            "name": "API v1 Root",
            "url": f"{base_url}/api/v1",
            "method": "GET",
            "description": "API v1 information and available endpoints"
        },
        {
            "name": "Main API Endpoint",
            "url": f"{base_url}/api/v1/hackrx/run",
            "method": "POST",
            "description": "Document query processing"
        },
        {
            "name": "Performance Stats",
            "url": f"{base_url}/performance",
            "method": "GET",
            "description": "Performance monitoring data"
        }
    ]
    
    for endpoint in endpoints_to_test:
        print(f"\n📍 {endpoint['name']}")
        print(f"   URL: {endpoint['url']}")
        print(f"   Method: {endpoint['method']}")
        print(f"   Description: {endpoint['description']}")
        
        try:
            if endpoint['method'] == 'GET':
                response = requests.get(endpoint['url'], timeout=5)
            else:
                # For POST endpoint, we'll just check if it responds (without auth)
                response = requests.post(endpoint['url'], timeout=5)
            
            if response.status_code == 200:
                print("   Status: ✅ Working")
                try:
                    data = response.json()
                    if 'message' in data:
                        print(f"   Response: {data['message']}")
                    elif 'endpoints' in data:
                        print("   Available endpoints:")
                        for key, value in data['endpoints'].items():
                            print(f"     - {key}: {value}")
                except:
                    print("   Response: Valid (non-JSON)")
            elif response.status_code == 401:
                print("   Status: ✅ Working (requires authentication)")
            elif response.status_code == 422:
                print("   Status: ✅ Working (requires valid request body)")
            else:
                print(f"   Status: ❌ Error {response.status_code}")
                
        except Exception as e:
            print(f"   Status: ❌ Connection error: {e}")
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY - Correct URLs to Use:")
    print("=" * 60)
    print(f"✅ API v1 Root: {base_url}/api/v1")
    print(f"✅ Main API: {base_url}/api/v1/hackrx/run (POST)")
    print(f"✅ Health: {base_url}/health")
    print(f"✅ Performance: {base_url}/performance")
    print("\n💡 Base URL: http://localhost:8000/api/v1")
    print("   Endpoint: /hackrx/run")
    print("   Full URL: http://localhost:8000/api/v1/hackrx/run")

if __name__ == "__main__":
    test_all_endpoints()