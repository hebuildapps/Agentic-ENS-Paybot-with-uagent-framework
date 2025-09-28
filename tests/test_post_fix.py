#!/usr/bin/env python3
"""
Quick test to verify POST / endpoint is fixed
"""
import requests
import time

def test_post_endpoint():
    """Test the POST / endpoint"""

    # Wait for server to be ready
    time.sleep(2)

    url = "http://127.0.0.1:10000"

    try:
        # Test simple GET first
        print("1. Testing GET /")
        response = requests.get(url)
        print(f"   Status: {response.status_code}")

        # Test POST with Agentverse-style message
        print("\n2. Testing POST / (Agentverse format)")
        payload = {
            "message": "Hello agent",
            "user_id": "test123"
        }

        response = requests.post(url, json=payload)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print(f"   Response: {response.json()}")
            print("\n✓ SUCCESS: POST / is working! 405 error is FIXED!")
        elif response.status_code == 405:
            print("   ✗ STILL BROKEN: 405 Method Not Allowed")
        else:
            print(f"   Unexpected status: {response.status_code}")
            print(f"   Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print("Could not connect to server on port 10000")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_post_endpoint()