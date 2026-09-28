#!/bin/bash
set -e

MODEL=${OLLAMA_MODEL:-qwen3:8b}
OS=$(uname -s)

echo "=== Health OS Setup ==="

# 1. Ollama
if ! command -v ollama &>/dev/null; then
  echo "▸ Installing Ollama..."
  if [ "$OS" = "Darwin" ]; then
    if ! command -v brew &>/dev/null; then
      echo "Homebrew not found. Install it first: https://brew.sh"
      exit 1
    fi
    brew install ollama
  else
    curl -fsSL https://ollama.com/install.sh | sh
  fi
else
  echo "▸ Ollama already installed"
fi

# 2. Start Ollama as background service
echo "▸ Starting Ollama..."
if [ "$OS" = "Darwin" ]; then
  brew services start ollama 2>/dev/null || true
else
  sudo systemctl enable --now ollama 2>/dev/null || ollama serve &>/dev/null &
fi

# Wait until ready
until curl -s http://localhost:11434/api/tags &>/dev/null; do
  sleep 2
done

# 3. Pull model
echo "▸ Pulling model $MODEL (one-time, ~5GB)..."
ollama pull "$MODEL"

# 4. .env check
if [ ! -f .env ]; then
  echo ""
  echo "⚠️  No .env found. Copy .env.example and fill in POSTGRES_PASSWORD:"
  echo "    cp .env.example .env"
  exit 1
fi

# 5. Docker services
echo "▸ Starting Docker services..."
docker compose up -d

echo ""
echo "✓ Done! Open WebUI → http://localhost:3000"
echo "  Default model: $MODEL"
echo "  To use a different model: OLLAMA_MODEL=qwen3:14b bash setup.sh"
