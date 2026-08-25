#!/bin/sh
embedding_model="${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}"
llm_model="${OLLAMA_LLM_MODEL:-llama3.2}"

ollama serve &

# Wait for server startup
sleep 5

echo "Pulling required models..."
ollama pull "$embedding_model"
ollama pull "$llm_model"

echo "Models are ready!"
wait
