# Use the official Ollama image as the base
FROM ollama/ollama:latest

# Install curl
# The base image is Ubuntu-based, so we use apt-get
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*
