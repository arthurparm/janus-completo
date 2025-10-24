# Exemplos de Código

Exemplos práticos para interagir com a API usando Python e cURL.

## Python (requests)

Criar ferramenta a partir de função:
```
import requests

payload = {
    "name": "text_summary",
    "description": "Resumir texto",
    "code": "def text_summary(text: str) -> str:\n    return text[:100]",
    "function_name": "text_summary",
    "category": "utility",
    "permission_level": "user",
    "rate_limit_per_min": 60,
    "tags": ["nlp", "summary"]
}

resp = requests.post("http://localhost:8000/api/v1/tools/create/from-function", json=payload)
print(resp.status_code, resp.json())
```

Agendar treinamento e consultar status:
```
import requests

train_payload = {
    "type": "Classifier",
    "dataset_id": "news-2024-09",
    "config": {"epochs": 3, "learning_rate": 0.0005}
}

ack = requests.post("http://localhost:8000/api/v1/learning/train", json=train_payload).json()
print("ACK:", ack)

status = requests.get("http://localhost:8000/api/v1/learning/training/status").json()
print("STATUS:", status)
```

Avaliar modelo:
```
import requests

payload = {
    "model_id": "model-123",
    "dataset_id": "news-2024-09",
    "metrics": ["accuracy", "f1"]
}

resp = requests.post("http://localhost:8000/api/v1/learning/evaluate", json=payload)
print(resp.json())
```

## cURL

Criar ferramenta de API HTTP:
```
curl -X POST http://localhost:8000/api/v1/tools/create/from-api \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ip_lookup",
    "description": "Consulta IP em serviço externo",
    "endpoint_url": "https://ipapi.co/json",
    "method": "GET",
    "headers": {"Accept": "application/json"},
    "category": "utility",
    "permission_level": "user",
    "rate_limit_per_min": 120,
    "tags": ["network", "lookup"]
  }'
```

Listar modelos:
```
curl -s http://localhost:8000/api/v1/learning/models
```