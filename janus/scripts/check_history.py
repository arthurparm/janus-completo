
import requests
import json
import sys

API_BASE = "http://localhost:8000/api/v1"

def check_chat_history(conversation_id):
    url = f"{API_BASE}/chat/{conversation_id}/history"
    try:
        print(f"Fetching history for conversation {conversation_id}...")
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        
        print(f"Conversation ID: {data.get('conversation_id')}")
        messages = data.get('messages', [])
        print(f"Total Messages: {len(messages)}")
        
        for i, msg in enumerate(messages):
            role = msg.get('role')
            text = msg.get('text', '')[:50] + "..." if len(msg.get('text', '')) > 50 else msg.get('text', '')
            print(f"[{i}] {role}: {text}")
            
    except Exception as e:
        print(f"Error fetching history: {e}")

if __name__ == "__main__":
    check_chat_history("47")
