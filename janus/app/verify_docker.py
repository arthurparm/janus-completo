import sys

import requests

# Inside Docker, localhost:8000 is the server itself
BASE_URL = "http://localhost:8000"


def log(msg):
    print(f"[TEST] {msg}")


def check_health():
    try:
        resp = requests.get(f"{BASE_URL}/health")
        if resp.status_code == 200:
            log("Health check PASSED")
            return True
        else:
            log(f"Health check FAILED: {resp.status_code}")
            return False
    except Exception as e:
        log(f"Health check ERROR: {e}")
        return False


def check_rag():
    try:
        # User Chat V1 (GET /user-chat)
        headers = {"X-User-Id": "test_user"}
        params = {"query": "test", "user_id": "test_user", "session_id": "test_verification_conv"}
        resp = requests.get(f"{BASE_URL}/api/v1/rag/user-chat", params=params, headers=headers)
        if resp.status_code == 200:
            log("RAG User Chat V1 PASSED")
        else:
            log(f"RAG User Chat V1 FAILED: {resp.status_code} - {resp.text}")

        # User Chat V2 (GET /user_chat)
        params_v2 = {"query": "test v2", "user_id": "test_user"}
        resp_v2 = requests.get(
            f"{BASE_URL}/api/v1/rag/user_chat", params=params_v2, headers=headers
        )
        if resp_v2.status_code == 200:
            log("RAG User Chat V2 PASSED")
        else:
            log(f"RAG User Chat V2 FAILED: {resp_v2.status_code} - {resp_v2.text}")

    except Exception as e:
        log(f"RAG check ERROR: {e}")


def check_chat():
    try:
        url = f"{BASE_URL}/api/v1/chat/message"
        payload = {
            "conversation_id": "test_chat_verification",
            "message": "test message",
            "role": "orchestrator",
            "priority": "fast_and_cheap",
        }
        with requests.post(url, json=payload, stream=True) as r:
            if r.status_code == 200:
                log("Chat Stream PASSED (connection established)")
                for line in r.iter_lines():
                    if line:
                        log(f"Chat Stream Data: {line.decode('utf-8')[:100]}")
                        break
            else:
                log(f"Chat Stream FAILED: {r.status_code} - {r.text}")
    except Exception as e:
        log(f"Chat check ERROR: {e}")


if __name__ == "__main__":
    if check_health():
        check_rag()
        check_chat()
    else:
        sys.exit(1)
