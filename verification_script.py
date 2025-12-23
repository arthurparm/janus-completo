import urllib.request
import json
import sys
import time

BASE_URL = "http://localhost:8000/api/v1"
HEALTH_URL = "http://localhost:8000/health"

def test_health():
    print(f"Checking {HEALTH_URL}...")
    try:
        with urllib.request.urlopen(HEALTH_URL) as response:
            if response.status != 200:
                print(f"FAIL: Health check returned {response.status}")
                return False
            data = json.loads(response.read().decode())
            print(f"SUCCESS: Health check passed. Status: {data.get('status')}")
            return True
    except Exception as e:
        print(f"FAIL: Health check exception: {e}")
        return False

def test_full_cycle():
    print("\nStarting Full Cycle Test...")
    
    # 1. Start Conversation
    print("1. Starting Conversation...")
    start_url = f"{BASE_URL}/chat/start"
    try:
        req = urllib.request.Request(start_url, data=json.dumps({}).encode('utf-8'), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            conversation_id = data.get("conversation_id")
            if not conversation_id:
                print("FAIL: No conversation_id returned")
                return False
            print(f"SUCCESS: Conversation started. ID: {conversation_id}")
    except Exception as e:
        print(f"FAIL: Start conversation exception: {e}")
        return False

    # 2. Send Message
    print("2. Sending Message (should utilize memory)...")
    msg_url = f"{BASE_URL}/chat/message"
    payload = {
        "conversation_id": conversation_id,
        "message": "Hello, I am testing the memory.",
        "role": "user"
    }
    try:
        req = urllib.request.Request(msg_url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        # Timeout slightly longer for LLM
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            response_text = data.get("response")
            if not response_text:
                 print("FAIL: No response text returned")
                 return False
            print(f"SUCCESS: Message sent. Response: {response_text[:100]}...")
    except Exception as e:
         print(f"FAIL: Send message exception: {e}")
         return False
         
    return True

if __name__ == "__main__":
    health_ok = test_health()
    if not health_ok:
        sys.exit(1)
        
    cycle_ok = test_full_cycle()
    if not cycle_ok:
        sys.exit(1)
    
    print("\nALL TESTS PASSED")
