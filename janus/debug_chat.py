import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_chat():
    print(f"Testing Chat API at {BASE_URL}...")
    
    # 1. Start Chat
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/chat/start",
            data=json.dumps({}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            cid = data['conversation_id']
            print(f"[SUCCESS] Started chat. CID: {cid}")
    except Exception as e:
        print(f"[ERROR] Failed to start chat: {e}")
        return

    # 2. Send Message
    payload = {
        "conversation_id": cid,
        "message": "Hello from debugger",
        "role": "orchestrator",
        "priority": "fast_and_cheap"
    }
    
    print(f"Sending payload: {json.dumps(payload, indent=2)}")
    
    try:
        req = urllib.request.Request(
            f"{BASE_URL}/chat/message",
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            print(f"Response Status: {response.status}")
            print(f"Response Body: {response.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        print(f"[HTTP ERROR] {e.code} {e.reason}")
        print(f"Error Body: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[ERROR] Failed to send message: {e}")

if __name__ == "__main__":
    test_chat()
