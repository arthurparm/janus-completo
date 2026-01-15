# Exemplos de Código

Exemplos práticos para interagir com a API usando Python e cURL. Todos os endpoints refletem o código atual. Para a visão consolidada, veja o [README.md](../README.md) principal.

## Python (requests)

Invocar LLM com roteamento adaptativo:
```
import requests

payload = {
  "prompt": "Explique a arquitetura do Janus em 3 tópicos",
  "role": "orchestrator",
  "priority": "fast_and_cheap"
}

resp = requests.post("http://localhost:8000/api/v1/llm/invoke", json=payload)
print(resp.status_code, resp.json())
```

Agendar treinamento e consultar status:
```
import requests

train_payload = {
  "dataset_id": "ds-2024-10",
  "model": "custom-bert",
  "epochs": 3
}

ack = requests.post("http://localhost:8000/api/v1/learning/train", json=train_payload).json()
print("ACK:", ack)

status = requests.get("http://localhost:8000/api/v1/learning/train/status", params={"job_id": ack.get("job_id")}).json()
print("STATUS:", status)
```

Consolidar conhecimento (batch):
```
import requests

resp = requests.post("http://localhost:8000/api/v1/knowledge/consolidate", json={
  "mode": "batch",
  "limit": 5,
  "min_score": 0.0
})
print(resp.json())
```

## cURL

Listar ferramentas:
```
curl -s http://localhost:8000/api/v1/tools
```

Criar ferramenta (API externa):
```
curl -X POST http://localhost:8000/api/v1/tools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "weather",
    "type": "http",
    "endpoint": "https://api.weather.com/v1/forecast",
    "category": "utilities",
    "permissions": ["network"],
    "tags": ["weather","forecast"]
  }'
```

Status de LLMs e circuit breakers:
```
curl -s http://localhost:8000/api/v1/llm/health
curl -s http://localhost:8000/api/v1/llm/circuit-breakers
```

Métricas Prometheus (amostra):
```
curl -s http://localhost:8000/metrics | head -n 50
```
