
import requests
import json
import time

API_BASE = "http://localhost:8000/api/v1"

def test_message(msg):
    print(f"\n--- Testing message: '{msg}' ---")
    url = f"{API_BASE}/chat/message"
    payload = {
        "conversation_id": "test_debug_47",
        "message": msg,
        "role": "auto",
        "priority": "fast_and_cheap"
    }
    
    start = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=60)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Response: {data.get('response', '')[:100]}...")
            print(f"Provider: {data.get('provider')}, Model: {data.get('model')}")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")
    finally:
        print(f"Time taken: {time.time() - start:.2f}s")

if __name__ == "__main__":
    test_message("Hello, are you online?")
    test_message("Explain how merge sort works step by step.")
