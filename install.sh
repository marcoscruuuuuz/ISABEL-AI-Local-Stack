#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "=============================================="
echo "  ISABEL AI Local Stack - Instalador Debian"
echo "  Versão: $(cat VERSION 2>/dev/null || echo '1.0.2')"
echo "=============================================="

echo "[1/8] Pacotes base..."
sudo apt-get update -qq
sudo apt-get install -y ca-certificates curl gnupg lsb-release git jq unzip \
  build-essential python3-pip python3-venv || true

echo "[2/8] Docker..."
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER" || true
fi
sudo apt-get install -y docker-compose-plugin || true

echo "[3/8] NVIDIA Container Toolkit..."
if ! dpkg -l | grep -q nvidia-container-toolkit; then
  distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
  sudo apt-get update -qq
  sudo apt-get install -y nvidia-container-toolkit
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
fi

echo "[4/8] Pastas..."
mkdir -p models data/qdrant data/workspace data/open-webui data/postgres data/redis corpus configs
cp -n .env.example .env || true

echo "[5/8] Sysctl performance..."
sudo tee /etc/sysctl.d/99-isabel.conf >/dev/null <<EOF
vm.max_map_count=262144
fs.file-max=2097152
net.core.somaxconn=1024
EOF
sudo sysctl --system || true

echo "[6/8] Modelo placeholder..."
if [ ! -e models/current-llm ]; then
  echo "Coloque o modelo em models/ e aponte models/current-llm"
  mkdir -p models/current-llm
fi

echo "[7/8] Build e up..."
docker compose build gateway
docker compose up -d postgres redis qdrant
sleep 5
docker compose up -d sglang gateway webui

echo "[8/8] Health check..."
sleep 8
curl -s localhost:8088/health || echo "Gateway ainda iniciando..."

echo ""
echo "=============================================="
echo "  Instalação concluída!"
echo "  UI OpenWebUI : http://<IP>:3000"
echo "  Gateway API  : http://<IP>:8088"
echo "  Health       : http://<IP>:8088/health"
echo "=============================================="
echo "Próximos passos:"
echo "  1. Edite .env (tokens, senhas, Cloudflare)"
echo "  2. ./scripts/pull_models.sh Qwen/Qwen2.5-14B-Instruct-AWQ"
echo "  3. docker compose --profile cloudflare up -d cloudflared"
echo "  4. Instale o ISABEL-Agent no Windows"
