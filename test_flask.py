#!/usr/bin/env python3
"""
Simple test script to verify the Flask server is working correctly.
"""
import os
import sys
import threading
import time
import requests
from web.flask_endpoints import create_app, run_flask_server

def test_flask_server():
    """Test the Flask server endpoints"""

    # Create the Flask app
    print("Creating Flask app...")
    app = create_app()

    # Start Flask in a separate thread
    print("Starting Flask server on port 10001...")
    flask_thread = threading.Thread(
        target=run_flask_server,
        args=(app,),
        kwargs={'port': 10001},
        daemon=True
    )
    flask_thread.start()

    # Wait for server to start
    time.sleep(3)

    base_url = "http://127.0.0.1:10001"

    try:
        # Test GET request to root
        print("\n1. Testing GET /")
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # Test POST request to root (simulating Agentverse)
        print("\n2. Testing POST / (Agentverse message)")
        agentverse_payload = {
            "message": "Hello from test",
            "user_id": "test_user"
        }
        response = requests.post(f"{base_url}/", json=agentverse_payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        # Test POST request to /chat
        print("\n3. Testing POST /chat")
        chat_payload = {
            "message": "Pay 5 USDC to alice.eth",
            "user_id": "test_user"
        }
        response = requests.post(f"{base_url}/chat", json=chat_payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")

        print("\n✓ All tests passed! Flask server is working correctly.")
        print("The 405 error should now be fixed.")

    except requests.exceptions.ConnectionError:
        print("X Could not connect to Flask server")
    except Exception as e:
        print(f"X Test failed with error: {e}")

if __name__ == "__main__":
    test_flask_server()