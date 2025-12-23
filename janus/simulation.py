import urllib.request
import json
import sys

# Using standard library to allow running in minimal environments
BASE_URL = "http://janus-api:8000/api/v1/chat"

def post_json(url, data):
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise

print("--- [SIMULACAO FRONTEND VIA DOCKER] ---")

print("\n1. Iniciando Conversa (/start)...")
try:
    resp = post_json(f"{BASE_URL}/start", {})
    cid = resp["conversation_id"]
    print(f"   Sucesso! Conversation ID: {cid}")
except Exception:
    sys.exit(1)

print(f"\n2. Enviando Mensagem (/message) na conversa {cid}...")
msg = {
    "conversation_id": cid,
    "message": "Ola via Docker. Se voce ler isso, o teste funcionou.",
    "role": "orchestrator",
    "priority": "local_only"
}
try:
    resp = post_json(f"{BASE_URL}/message", msg)
    print(f"   Resposta do Janus: {resp['response']}")
    print("\n✅ TESTE CONCLUIDO COM SUCESSO")
except Exception:
    sys.exit(1)
