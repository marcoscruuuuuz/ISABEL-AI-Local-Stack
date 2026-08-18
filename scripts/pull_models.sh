#!/usr/bin/env bash
set -euo pipefail
MODEL=${1:-Qwen/Qwen2.5-14B-Instruct-AWQ}
DEST=${MODELS_DIR:-/opt/isabel/models}
mkdir -p "$DEST"
echo "Baixando $MODEL ..."
huggingface-cli download "$MODEL" --local-dir "$DEST/$(basename "$MODEL")" || {
  echo "Falha no download. Instale: pip install -U huggingface_hub"
  exit 1
}
ln -sfn "$DEST/$(basename "$MODEL")" "$DEST/current-llm"
echo "Modelo ativo: $DEST/current-llm"
