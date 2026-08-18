#!/usr/bin/env bash
# ISABEL AI Local Stack — Bootstrap Debian (instalação nova)
# Uso:
#   curl -fsSL https://raw.githubusercontent.com/marcoscruuuuuz/ISABEL-AI-Local-Stack/main/scripts/bootstrap-debian.sh | sudo bash
# ou:
#   sudo bash bootstrap-debian.sh
# Opções:
#   WITH_GPU=1 WITH_CLOUDFLARE=1 sudo -E bash bootstrap-debian.sh
set -euo pipefail

ISABEL_DIR="${ISABEL_DIR:-/opt/isabel}"
REPO_URL="${REPO_URL:-https://github.com/marcoscruuuuuz/ISABEL-AI-Local-Stack.git}"
BRANCH="${BRANCH:-main}"
WITH_GPU="${WITH_GPU:-0}"
WITH_CLOUDFLARE="${WITH_CLOUDFLARE:-0}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[ISABEL]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $*"; }
err()  { echo -e "${RED}[ERRO]${NC} $*"; exit 1; }

[[ $EUID -eq 0 ]] || err "Execute como root: sudo bash $0"

echo ""
echo "=============================================="
echo "  ISABEL AI Local Stack — Bootstrap Debian"
echo "=============================================="
echo "  Destino: $ISABEL_DIR"
echo "  Branch:  $BRANCH"
echo "  GPU:     $WITH_GPU"
echo "  CF:      $WITH_CLOUDFLARE"
echo "=============================================="
echo ""

log "Atualizando sistema e pacotes base..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git jq openssl gnupg lsb-release apt-transport-https software-properties-common ufw > /dev/null
ok "Pacotes base instalados"

if command -v docker >/dev/null 2>&1; then
  ok "Docker já instalado: $(docker --version)"
else
  log "Instalando Docker Engine + Compose plugin..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  ok "Docker instalado"
fi
docker compose version >/dev/null 2>&1 || err "docker compose plugin não encontrado"

if [[ "$WITH_GPU" == "1" ]]; then
  if command -v nvidia-smi >/dev/null 2>&1; then
    log "GPU detectada. Instalando nvidia-container-toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' > /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -qq
    apt-get install -y -qq nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    ok "NVIDIA Container Toolkit configurado"
  else
    warn "WITH_GPU=1 mas nvidia-smi não encontrado. Continuando sem GPU."
    WITH_GPU=0
  fi
fi

if [[ -d "$ISABEL_DIR/.git" ]]; then
  log "Atualizando repositório em $ISABEL_DIR..."
  git -C "$ISABEL_DIR" fetch --all
  git -C "$ISABEL_DIR" checkout "$BRANCH"
  git -C "$ISABEL_DIR" pull --ff-only origin "$BRANCH" || true
else
  log "Clonando ISABEL em $ISABEL_DIR..."
  mkdir -p "$(dirname "$ISABEL_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$ISABEL_DIR"
fi
cd "$ISABEL_DIR"
ok "Código em $ISABEL_DIR"

if [[ ! -f .env ]]; then
  log "Gerando .env com segredos aleatórios..."
  API_TOKEN=$(openssl rand -hex 32)
  POSTGRES_PASSWORD=$(openssl rand -hex 24)
  JWT_SECRET=$(openssl rand -hex 32)
  WEBUI_SECRET=$(openssl rand -hex 24)
  ADMIN_PASS=$(openssl rand -hex 12)
  cat > .env << ENVEOF
ISABEL_VERSION=1.0.2
API_TOKEN=${API_TOKEN}
JWT_SECRET=${JWT_SECRET}
ADMIN_USER=admin
ADMIN_PASS=${ADMIN_PASS}
WEBUI_SECRET=${WEBUI_SECRET}
POSTGRES_DB=isabel
POSTGRES_USER=isabel
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
SGLANG_URL=http://sglang:30000
SGLANG_MODEL_PATH=/models/host/current-llm
MEM_FRACTION_STATIC=0.80
MAX_MODEL_LEN=8192
TP_SIZE=1
CUDA_VISIBLE_DEVICES=0
MODELS_DIR=./models
GATEWAY_PORT=8088
ADMIN_PORT=3001
WEBUI_PORT=3000
TOKEN_PRICE_PER_1K=0.02
CLOUDFLARE_TUNNEL_TOKEN=
CF_ACCESS_CLIENT_ID=
CF_ACCESS_CLIENT_SECRET=
CF_HOSTNAME=
ENVEOF
  chmod 600 .env
  ok ".env criado"
  HOST_IP=$(hostname -I | awk '{print $1}')
  cat > /root/isabel-credentials.txt << CREDEOF
ISABEL — Credenciais geradas em $(date -Iseconds)
================================================
API_TOKEN=${API_TOKEN}
ADMIN_USER=admin
ADMIN_PASS=${ADMIN_PASS}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
JWT_SECRET=${JWT_SECRET}
WEBUI_SECRET=${WEBUI_SECRET}

Admin UI:  http://${HOST_IP}:3001/admin/
Chat UI:   http://${HOST_IP}:3001/chat/
API:       http://${HOST_IP}:8088/health
CREDEOF
  chmod 600 /root/isabel-credentials.txt
  ok "Credenciais em /root/isabel-credentials.txt"
else
  ok ".env já existe — mantendo"
fi

log "Preparando diretórios..."
mkdir -p models corpus data/workspace
chmod +x scripts/*.sh install.sh 2>/dev/null || true

if command -v ufw >/dev/null 2>&1; then
  log "Configurando UFW..."
  ufw allow OpenSSH >/dev/null 2>&1 || ufw allow 22/tcp >/dev/null 2>&1 || true
  ufw allow 8088/tcp comment 'ISABEL Gateway' >/dev/null 2>&1 || true
  ufw allow 3001/tcp comment 'ISABEL Frontend' >/dev/null 2>&1 || true
  if ufw status 2>/dev/null | grep -q inactive; then
    warn "UFW inativo. Depois: ufw --force enable"
  else
    ufw reload >/dev/null 2>&1 || true
  fi
fi

log "Build e start dos containers (core)..."
docker compose pull || true
docker compose build --pull
docker compose up -d

if [[ "$WITH_GPU" == "1" ]]; then
  log "Subindo profile GPU..."
  docker compose --profile gpu up -d || warn "Profile GPU falhou"
fi

if [[ "$WITH_CLOUDFLARE" == "1" ]]; then
  if grep -q '^CLOUDFLARE_TUNNEL_TOKEN=.\+' .env 2>/dev/null; then
    docker compose --profile cloudflare up -d
  else
    warn "CLOUDFLARE_TUNNEL_TOKEN vazio no .env"
  fi
fi

log "Aguardando Gateway..."
HOST_IP=$(hostname -I | awk '{print $1}')
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:8088/health" >/dev/null 2>&1; then
    ok "Gateway online"
    break
  fi
  [[ $i -eq 60 ]] && warn "Timeout health. Ver: docker compose logs gateway --tail=50"
  sleep 2
done

echo ""
echo "=============================================="
echo "  ISABEL — Status"
echo "=============================================="
docker compose ps
echo ""
curl -s "http://127.0.0.1:8088/health" 2>/dev/null | jq . 2>/dev/null || curl -s "http://127.0.0.1:8088/health" || true
echo ""
echo "  Health:  http://${HOST_IP}:8088/health"
echo "  Admin:   http://${HOST_IP}:3001/admin/"
echo "  Chat:    http://${HOST_IP}:3001/chat/"
echo "  Creds:   /root/isabel-credentials.txt"
echo ""
echo "  Próximos passos:"
echo "  1. Abra Admin e cadastre AGENTE-PC-..."
echo "  2. Windows: claim_and_install.ps1 -InstallKey XXXX -ServerApi http://${HOST_IP}:8088"
echo "  3. GPU: ./scripts/pull_models.sh ... && docker compose --profile gpu up -d"
echo "=============================================="
ok "Bootstrap concluído."
