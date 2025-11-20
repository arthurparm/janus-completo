#!/bin/sh

# fail fast em shells compatíveis; ignorar se indisponível
set -e || true

ollama serve &

echo "Waiting for Ollama server to be ready..."
while ! curl -s -f http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done
echo "Ollama server is ready."

echo "Pulling orchestrator model: llama3.1:8b"
ollama pull llama3.1:8b

echo "Pulling coder model: codellama:7b"
ollama pull codellama:7b

echo "Pulling curator model: phi3:mini"
ollama pull phi3:mini

echo "Model pulling complete."

echo "Pre-warming models to reduce first-request latency..."
curl -sS -X POST http://localhost:11434/api/generate \
  -d '{"model":"llama3.1:8b","prompt":"ping","keep_alive":"30m"}' > /dev/null || true
curl -sS -X POST http://localhost:11434/api/generate \
  -d '{"model":"codellama:7b","prompt":"ping","keep_alive":"30m"}' > /dev/null || true
curl -sS -X POST http://localhost:11434/api/generate \
  -d '{"model":"phi3:mini","prompt":"ping","keep_alive":"30m"}' > /dev/null || true

wait