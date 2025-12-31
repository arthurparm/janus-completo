#!/bin/sh

# fail fast em shells compatíveis; ignorar se indisponível
set -e || true

ollama serve &

echo "Waiting for Ollama server to be ready..."
while ! curl -s -f http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done
echo "Ollama server is ready."

echo "Pulling orchestrator/curator model: qwen2.5:14b"
ollama pull qwen2.5:14b

echo "Pulling coder model: qwen2.5-coder:14b"
ollama pull qwen2.5-coder:14b

echo "Model pulling complete."

echo "Pre-warming models to reduce first-request latency..."
curl -sS -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:14b","prompt":"ping","keep_alive":"30m"}' > /dev/null || true
curl -sS -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5-coder:14b","prompt":"ping","keep_alive":"30m"}' > /dev/null || true

wait