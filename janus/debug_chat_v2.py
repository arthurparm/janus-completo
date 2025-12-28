import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_chat():
    print(f"Testing Chat API at {BASE_URL}...")
    
    # Test with HARDCODED UUID to check Pydantic validation independently of start_chat
    fake_cid = "123e4567-e89b-12d3-a456-426614174000"
    payload = {
        "conversation_id": fake_cid,
        "message": "Hello from debugger",
        "role": "orchestrator",
        "priority": "fast_and_cheap"
    }
    
    print(f"Sending payload with FAKE CID: {json.dumps(payload)}")
    
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/chat/message",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            print(f"Response Status: {response.status}")
    except urllib.error.HTTPError as e:
        print(f"[HTTP ERROR] {e.code} {e.reason}")
        print(f"Error Body: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    test_chat()
