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

# Pull qwen2.5:14b
if ! curl -sf http://localhost:11434/api/tags | grep -q '"model":"qwen2.5:14b"'; then
    echo "Pulling qwen2.5:14b..."
    ollama pull qwen2.5:14b
else
    echo "Model qwen2.5:14b already exists"
fi

# Pull qwen2.5-coder:14b
if ! curl -sf http://localhost:11434/api/tags | grep -q '"model":"qwen2.5-coder:14b"'; then
    echo "Pulling qwen2.5-coder:14b..."
    ollama pull qwen2.5-coder:14b
else
    echo "Model qwen2.5-coder:14b already exists"
fi

echo "All models pulled successfully!"
echo "Ollama is ready to serve requests"

# Keep the service running
wait $OLLAMA_PID
