#!/usr/bin/env python3
"""
Test the POST endpoint specifically
"""

import requests
import json

def test_post_endpoint():
    """Test the POST endpoint with proper request"""
    
    url = "http://localhost:8000/api/v1/hackrx/run"
    
    # Test data
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
    
    print("🧪 Testing POST Endpoint")
    print("=" * 50)
    print(f"URL: {url}")
    print(f"Method: POST")
    print(f"Request data: {json.dumps(request_data, indent=2)}")
    print("=" * 50)
    
    try:
        print("Making POST request...")
        response = requests.post(
            url,
            json=request_data,
            headers=headers,
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ POST request successful!")
            result = response.json()
            print(f"Number of answers: {len(result.get('answers', []))}")
            for i, answer in enumerate(result.get('answers', []), 1):
                print(f"Answer {i}: {answer[:100]}...")
        elif response.status_code == 401:
            print("❌ Authentication error - check API key")
        elif response.status_code == 422:
            print("❌ Request format error")
            try:
                error_detail = response.json()
                print(f"Error details: {json.dumps(error_detail, indent=2)}")
            except:
                print(f"Raw error: {response.text}")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - is the server running?")
        print("Start the server with: python start_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_post_endpoint()