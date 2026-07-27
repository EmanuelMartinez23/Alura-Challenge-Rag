#!/bin/sh
set -e

export OLLAMA_HOST=${OLLAMA_HOST:-http://ollama:11434}

echo "Esperando al servicio de Ollama en ${OLLAMA_HOST}..."
until ollama list >/dev/null 2>&1; do
    sleep 2
done

echo "Descargando modelos requeridos..."
ollama pull bge-m3:latest
ollama pull gemma3:4b
ollama pull gemma3:1b

echo "Todos los modelos están listos."
