#!/bin/sh
# Exit immediately if a command exits with a non-zero status.
set -e

# Start the Ollama server in the background
ollama serve &

# Wait for the server to be ready by polling the /api/tags endpoint
echo "Waiting for Ollama server to be ready..."
while ! curl -s -f http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done
echo "Ollama server is ready."

# Pull the required models
echo "Pulling orchestrator model: llama3.1:8b"
ollama pull llama3.1:8b

echo "Pulling coder model: codellama:7b"
ollama pull codellama:7b

echo "Pulling curator model: phi3:mini"
ollama pull phi3:mini

echo "Model pulling complete."

# Bring the background server process to the foreground
# This ensures the container keeps running
wait
