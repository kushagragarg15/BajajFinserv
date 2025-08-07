#!/usr/bin/env python3
"""
Server Diagnostic Script

This script helps diagnose issues with the running server by testing different endpoints
and request formats to identify the specific problem.
"""

import requests
import json
import sys
from typing import Dict, Any

def test_server_health():
    """Test basic server health"""
    print("🔍 Testing server health...")
    
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        print(f"Health endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"Server status: {health_data.get('overall_status', 'unknown')}")
            print("✅ Server is responding to health checks")
            return True
        else:
            print(f"❌ Health check failed with status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_root_endpoint():
    """Test root endpoint"""
    print("\n🔍 Testing root endpoint...")
    
    try:
        response = requests.get("http://localhost:8001/", timeout=10)
        print(f"Root endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Root endpoint is working")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Root endpoint failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")
        return False

def test_api_endpoint_with_valid_request():
    """Test API endpoint with a properly formatted request"""
    print("\n🔍 Testing API endpoint with valid request...")
    
    # Proper request format
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
        print("Making request to /api/v1/hackrx/run...")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            "http://localhost:8001/api/v1/hackrx/run",
            json=request_data,
            headers=headers,
            timeout=30
        )
        
        print(f"API endpoint status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API endpoint is working correctly")
            result = response.json()
            print(f"Number of answers received: {len(result.get('answers', []))}")
            return True
        else:
            print(f"❌ API endpoint failed with status: {response.status_code}")
            print("Response headers:", dict(response.headers))
            print("Response body:", response.text)
            
            # Try to parse error details
            try:
                error_data = response.json()
                print("Error details:", json.dumps(error_data, indent=2))
            except:
                print("Could not parse error response as JSON")
            
            return False
            
    except Exception as e:
        print(f"❌ API endpoint error: {e}")
        return False

def test_common_request_issues():
    """Test common request format issues"""
    print("\n🔍 Testing common request format issues...")
    
    headers = {
        "Authorization": "Bearer 04882ff997f04a7548a2640b6ac4ca31bb61a48594229f92000cc82b4e6dbd3d",
        "Content-Type": "application/json"
    }
    
    # Test cases for common issues
    test_cases = [
        {
            "name": "Missing questions field",
            "data": {
                "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
            }
        },
        {
            "name": "Empty questions array",
            "data": {
                "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "questions": []
            }
        },
        {
            "name": "Invalid URL format",
            "data": {
                "documents": "not-a-valid-url",
                "questions": ["What is this?"]
            }
        },
        {
            "name": "Missing documents field",
            "data": {
                "questions": ["What is this?"]
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        try:
            response = requests.post(
                "http://localhost:8001/api/v1/hackrx/run",
                json=test_case['data'],
                headers=headers,
                timeout=10
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    print(f"Error: {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"Raw error: {response.text}")
        except Exception as e:
            print(f"Request failed: {e}")

def test_authentication():
    """Test authentication issues"""
    print("\n🔍 Testing authentication...")
    
    request_data = {
        "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
        "questions": ["What is this?"]
    }
    
    # Test without auth
    print("Testing without authentication...")
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/hackrx/run",
            json=request_data,
            timeout=10
        )
        print(f"No auth status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Authentication is properly required")
        else:
            print("⚠️ Authentication may not be working correctly")
    except Exception as e:
        print(f"No auth test failed: {e}")
    
    # Test with wrong auth
    print("Testing with wrong authentication...")
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/hackrx/run",
            json=request_data,
            headers={"Authorization": "Bearer wrong-token"},
            timeout=10
        )
        print(f"Wrong auth status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Authentication validation is working")
        else:
            print("⚠️ Authentication validation may have issues")
    except Exception as e:
        print(f"Wrong auth test failed: {e}")

def main():
    """Main diagnostic function"""
    print("🚀 Server Diagnostic Tool")
    print("=" * 50)
    
    # Test 1: Basic connectivity
    if not test_server_health():
        print("\n❌ Server health check failed. Server may not be running properly.")
        return False
    
    # Test 2: Root endpoint
    test_root_endpoint()
    
    # Test 3: Authentication
    test_authentication()
    
    # Test 4: Valid API request
    if test_api_endpoint_with_valid_request():
        print("\n✅ Server appears to be working correctly!")
        print("The 422 error you saw might be due to request format issues.")
        return True
    
    # Test 5: Common request issues
    test_common_request_issues()
    
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    print("If you're still getting 422 errors, check:")
    print("1. Request format matches the expected schema")
    print("2. All required fields are present")
    print("3. Data types are correct (URL as string, questions as array)")
    print("4. Content-Type header is set to 'application/json'")
    print("5. Authorization header is properly formatted")
    
    return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Diagnostic interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        sys.exit(1)