# ISABEL AI Local Stack

**Sistema comercial de IA local offline-first**  
Chat · Deep Research · Multi-agente · Frota Windows 2B · Multi-tenant · Cloudflare

**Versão:** 1.0.2 · **Repo:** https://github.com/marcoscruuuuuz/ISABEL-AI-Local-Stack

## Documentação completa

- **[docs/SYSTEM_COMPLETE.md](docs/SYSTEM_COMPLETE.md)** — arquitetura, API, frota, deploy, maturidade, vs Cursor/Codex
- [docs/DEPLOYMENT_SERVER.md](docs/DEPLOYMENT_SERVER.md) — instalação Debian
- [docs/FLEET_AGENTS.md](docs/FLEET_AGENTS.md) — agentes Windows 2B
- [docs/rules/](docs/rules/) — regras de execução da ISABEL

## Subir rápido (sem GPU)

```bash
cp .env.example .env   # defina POSTGRES_PASSWORD e API_TOKEN
docker compose up -d --build
# Admin http://IP:3001/admin/  ·  Chat http://IP:3001/chat/
```

Com GPU: `docker compose --profile gpu up -d`  
Com Cloudflare: `docker compose --profile cloudflare up -d`

## Arquitetura (resumo)

```
Windows: fleet_agent + modelo 2B  ──WSS──►  Cloudflare  ──►  Debian
  Gateway FastAPI · SGLang · Qdrant · Redis · Postgres · Admin/Chat
```

## Uso no chat

```
AGENTE-PC-financeiro01 quantos R$ foram lançados hoje?
```

## Hardware alvo

RTX 12GB+ · CPU multi-core · 32–64 GB RAM · SSD para modelos

## Licença

Uso conforme contrato comercial (Innovation RP Telecom).
