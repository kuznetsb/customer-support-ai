#!/bin/sh
ollama serve &

# Wait for server startup
sleep 5

echo "Pulling required models..."
ollama pull nomic-embed-text
ollama pull llama3.2

echo "Models are ready!"
wait
