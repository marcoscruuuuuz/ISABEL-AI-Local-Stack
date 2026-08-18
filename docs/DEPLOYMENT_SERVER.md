# ISABEL - Implantacao do Servidor

## Debian
```bash
git clone https://github.com/marcoscruuuuuz/ISABEL-AI-Local-Stack.git /opt/isabel
cd /opt/isabel
cp .env.example .env
# Edite tokens e senhas
./install.sh
./scripts/pull_models.sh Qwen/Qwen2.5-14B-Instruct-AWQ
docker compose up -d
```

## Verificacao
```bash
curl http://localhost:8088/health
# Admin: http://IP:3001/admin/
# Chat:  http://IP:3001/chat/
```

## Cloudflare
```bash
docker compose --profile cloudflare up -d cloudflared
```
