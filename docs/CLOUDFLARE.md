# Cloudflare Tunnel + Access

1. Crie Tunnel e Service Token no Zero Trust
2. No .env:
```
CLOUDFLARE_TUNNEL_TOKEN=...
CF_ACCESS_CLIENT_ID=...
CF_ACCESS_CLIENT_SECRET=...
CF_HOSTNAME=ai.seudominio.com.br
```
3. `docker compose --profile cloudflare up -d cloudflared`

Nenhuma porta do servidor precisa ser exposta na internet.
