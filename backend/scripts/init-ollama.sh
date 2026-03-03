#!/bin/sh
set -e

echo "Starting Ollama service..."
/bin/ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama to be ready..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "Ollama is ready!"
        break
    fi
    echo "Attempt $i/30: Ollama not ready yet..."
    sleep 2
done

if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama failed to start after 60 seconds"
    exit 1
fi

echo "Pulling required models..."

ORCH_MODEL="${OLLAMA_ORCHESTRATOR_MODEL:-qwen2.5:14b}"
CODER_MODEL="${OLLAMA_CODER_MODEL:-qwen2.5-coder:14b}"
CURATOR_MODEL="${OLLAMA_CURATOR_MODEL:-qwen2.5:14b}"

pull_if_missing() {
    model="$1"
    if ! curl -sf http://localhost:11434/api/tags | grep -q "\"model\":\"$model\""; then
        echo "Pulling $model..."
        ollama pull "$model"
    else
        echo "Model $model already exists"
    fi
}

pull_if_missing "$ORCH_MODEL"
pull_if_missing "$CODER_MODEL"
pull_if_missing "$CURATOR_MODEL"

echo "All models pulled successfully!"
echo "Ollama is ready to serve requests"

# Keep the service running
wait $OLLAMA_PID
