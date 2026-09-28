#!/bin/bash
set -e

echo "=== Reinstall Ollama (Intel → ARM native) ==="

# 1. Зупини і видали Intel-версію
echo "▸ Stopping Intel Ollama..."
/usr/local/bin/brew services stop ollama 2>/dev/null || true

echo "▸ Uninstalling Intel Ollama..."
/usr/local/bin/brew uninstall --ignore-dependencies ollama 2>/dev/null || true

# 2. Встанови ARM Homebrew якщо нема
if [ ! -f /opt/homebrew/bin/brew ]; then
  echo "▸ Installing Apple Silicon Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
  echo "▸ ARM Homebrew already installed"
fi

# 3. Встанови Ollama через ARM brew
echo "▸ Installing native ARM Ollama..."
/opt/homebrew/bin/brew install ollama

# 4. Запусти
echo "▸ Starting Ollama (ARM)..."
/opt/homebrew/bin/brew services start ollama

# 5. Чекай поки стартує
until curl -s http://localhost:11434/api/tags &>/dev/null; do sleep 2; done

# 6. Перевір GPU
echo ""
echo "✓ Done! GPU status:"
ollama ps 2>/dev/null || echo "(запусти: ollama run qwen3:8b — і перевір)"

echo ""
echo "Моделі збережені, перекачувати не треба:"
ollama list
