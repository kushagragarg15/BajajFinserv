#!/usr/bin/env python3
"""
Test Your Request Format

This script helps you test the exact request format you're using
to identify what's causing the 422 error.
"""

import requests
import json
import sys

def test_request_format():
    """Test different request formats to identify the issue"""
    
    # The working format (based on the test server success)
    working_request = {
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
    
    print("🧪 Testing Request Formats")
    print("=" * 50)
    
    # Test 1: Test server (should work)
    print("\n1. Testing with simple test server (port 8001)...")
    try:
        response = requests.post(
            "http://localhost:8001/api/v1/hackrx/run",
            json=working_request,
            headers=headers,
            timeout=10
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Test server works! Got {len(result['answers'])} answers")
        else:
            print(f"❌ Test server failed: {response.text}")
    except Exception as e:
        print(f"❌ Test server error: {e}")
    
    # Test 2: Full server (port 8000) - this is where your 422 error occurs
    print("\n2. Testing with full optimized server (port 8000)...")
    try:
        response = requests.post(
            "http://localhost:8000/api/v1/hackrx/run",
            json=working_request,
            headers=headers,
            timeout=30
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Full server works! Got {len(result['answers'])} answers")
        elif response.status_code == 422:
            print("❌ 422 Error - Unprocessable Entity")
            try:
                error_detail = response.json()
                print("Error details:")
                print(json.dumps(error_detail, indent=2))
            except:
                print("Raw error response:")
                print(response.text)
        else:
            print(f"❌ Full server error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Full server connection error: {e}")
    
    # Test 3: Check what format might be causing issues
    print("\n3. Testing common problematic formats...")
    
    problematic_formats = [
        {
            "name": "String instead of array for questions",
            "data": {
                "documents": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "questions": "What is this document about?"  # String instead of array
            }
        },
        {
            "name": "Missing documents field",
            "data": {
                "questions": ["What is this document about?"]
            }
        },
        {
            "name": "Wrong field name (document instead of documents)",
            "data": {
                "document": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "questions": ["What is this document about?"]
            }
        },
        {
            "name": "Invalid URL format",
            "data": {
                "documents": "not-a-valid-url",
                "questions": ["What is this document about?"]
            }
        }
    ]
    
    for test_case in problematic_formats:
        print(f"\nTesting: {test_case['name']}")
        try:
            response = requests.post(
                "http://localhost:8001/api/v1/hackrx/run",  # Test with simple server first
                json=test_case['data'],
                headers=headers,
                timeout=10
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 422:
                print("This format causes 422 error!")
                try:
                    error_detail = response.json()
                    print("Error details:")
                    print(json.dumps(error_detail, indent=2))
                except:
                    print("Raw error:", response.text)
        except Exception as e:
            print(f"Request failed: {e}")

def show_correct_format():
    """Show the correct request format"""
    print("\n" + "=" * 60)
    print("CORRECT REQUEST FORMAT")
    print("=" * 60)
    
    correct_format = {
        "documents": "https://example.com/document.pdf",
        "questions": [
            "Question 1?",
            "Question 2?",
            "Question 3?"
        ]
    }
    
    print("JSON Body:")
    print(json.dumps(correct_format, indent=2))
    
    print("\nHeaders:")
    print("Authorization: Bearer 04882ff997f04a7548a2640b6ac4ca31bb61a48594229f92000cc82b4e6dbd3d")
    print("Content-Type: application/json")
    
    print("\nCURL Example:")
    curl_command = f'''curl -X POST "http://localhost:8000/api/v1/hackrx/run" \\
     -H "Authorization: Bearer 04882ff997f04a7548a2640b6ac4ca31bb61a48594229f92000cc82b4e6dbd3d" \\
     -H "Content-Type: application/json" \\
     -d '{json.dumps(correct_format)}'
'''
    print(curl_command)

def main():
    """Main function"""
    test_request_format()
    show_correct_format()
    
    print("\n" + "=" * 60)
    print("TROUBLESHOOTING TIPS")
    print("=" * 60)
    print("If you're still getting 422 errors:")
    print("1. Make sure 'documents' field contains a valid URL (not 'document')")
    print("2. Make sure 'questions' is an array of strings (not a single string)")
    print("3. Make sure Content-Type header is 'application/json'")
    print("4. Make sure the JSON is properly formatted")
    print("5. Check that the Authorization header is correct")
    print("6. Verify the server is running the optimized version, not an old version")

if __name__ == "__main__":
    main()