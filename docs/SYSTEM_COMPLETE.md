# ISABEL AI Local Stack — Documentação Completa do Sistema

**Versão:** 1.0.2  
**Repositório:** https://github.com/marcoscruuuuuz/ISABEL-AI-Local-Stack  
**Tipo:** Sistema comercial de IA local offline-first (servidor Debian + agentes Windows)

---

## 1. O que é o ISABEL

O ISABEL é uma plataforma de IA **privativa e local** que combina:

1. **Servidor central (Debian)** — LLM pesado (14B+), chat web, admin comercial, multi-agentes de código, Deep Research, billing de tokens.
2. **Frota de agentes Windows (até 100)** — cada um com modelo **2B quantizado**, acesso controlado a arquivos/sistemas do PC, conexão só de saída (WSS), offline-first.
3. **Chat unificado** — a ISABEL central orquestra respostas do modelo servidor **ou** de um agente local específico (`AGENTE-PC-financeiro01 ...`).

### Diferencial vs Cursor / Codex

| Aspecto | Cursor / Codex | ISABEL |
|---------|----------------|--------|
| Dados do cliente | Nuvem do fornecedor | Seu servidor / PC |
| Agentes no Windows do cliente | Não | Até 100 agentes 2B por conta |
| Offline | Limitado | Servidor local + agente 2B offline |
| Comercial multi-tenant | Não | Planos, tokens, tenants, admin |
| Modelo no instalador Windows | Não | 2B GGUF no PC do cliente |
| Acesso a ERP/planilha local | Não | Allowlist + local_systems |

Cursor/Codex são excelentes **IDEs na nuvem**. O ISABEL é um **stack completo dono-do-dado** (servidor + frota + comercial).

---

## 2. Arquitetura geral

```
PC Windows (cliente)
  fleet_agent.py + Modelo 2B (127.0.0.1:11434)
       │ WSS outbound + CF Access Token
       ▼
Cloudflare Tunnel + Access (opcional)
       ▼
Servidor Debian
  Gateway FastAPI :8088
  SGLang LLM :30000 (profile gpu)
  Qdrant · Redis · Postgres
  Frontend Admin/Chat :3001
```

### Dois cérebros

| Cérebro | Onde | Modelo | Quando usar |
|---------|------|--------|-------------|
| Central | Servidor | 14B+ (SGLang) | Chat, código, research, multi-agente |
| Local 2B | Windows | Qwen2.5-1.5B Q4 | Dados deste PC, offline, ERP/planilha |

---

## 3. Componentes do repositório

- `server/` — Gateway FastAPI (main, routers, db, services)
- `client/windows/fleet/` — fleet_agent.py + claim_and_install.ps1
- `web/dist/admin` e `web/dist/chat` — UIs
- `configs/init.sql` — schema Postgres (tenants, fleet, tokens)
- `docker-compose.yml` — profiles: default, gpu, cloudflare
- `docs/` — manuais e regras

---

## 4. API — mapa de endpoints

Base: `http://GATEWAY:8088` · Auth: `Authorization: Bearer <API_TOKEN>` · Tenant: `X-Tenant-Id`

### Core
GET `/health` · GET `/v1/models` · POST `/v1/chat/completions` · POST `/chat` · POST `/research` · POST `/agent/run` · POST `/multi-agent/run` · POST `/multi-agent/plan`

### Comercial
GET `/admin/plans` · POST/GET `/admin/tenants` · GET `/admin/usage/{id}` · POST `/billing/consume` · GET `/billing/summary/{id}`

### Frota
POST/GET/DELETE `/fleet/agents` · POST `/fleet/agents/claim` · POST `/fleet/agents/{id}/heartbeat` · POST `/fleet/query` · GET `/fleet/stats` · GET `/fleet/usage` · WS `/ws/fleet/{agent_id}`

---

## 5. Fluxo comercial e frota

1. Admin cadastra `AGENTE-PC-financeiro01` + sistemas locais → gera `install_key`
2. Windows: `claim_and_install.ps1 -InstallKey XXXX -ServerApi https://...`
3. Chat: `AGENTE-PC-financeiro01 quantos R$ foram lançados hoje?`
4. Se WS online → query ao 2B e resposta no chat; se offline → offline_cache

---

## 6. Regras de execução

Ver `docs/rules/ISABEL_MAIN_RULES.md`, `SERVER_AGENTS_RULES.md`, `LOCAL_AGENT_RULES.md`.

Prioridade: Segurança > precisão > economia de tokens. Dados de um PC → agente local. Código/research → servidor.

---

## 7. Persistência (Postgres)

tenants · plans · token_usage · fleet_agents · fleet_queries · audit_log  
Fallback: memória se Postgres offline (`/health` → `"db": false`).

---

## 8. Deploy

```bash
git clone https://github.com/marcoscruuuuuz/ISABEL-AI-Local-Stack.git /opt/isabel
cd /opt/isabel && cp .env.example .env
# Editar POSTGRES_PASSWORD, API_TOKEN
docker compose up -d --build
docker compose --profile gpu up -d          # opcional
docker compose --profile cloudflare up -d  # opcional
curl -s http://localhost:8088/health
```

Admin: `:3001/admin/` · Chat: `:3001/chat/`

---

## 9. Segurança

Tunnel Cloudflare · Service Token · agent_token por agente · allowlist Windows · shell off · sandbox /workspace · 2B só em 127.0.0.1 · secrets só no .env

---

## 10. Maturidade real

| Camada | Estimativa |
|--------|------------|
| Core API + UI | ~85% |
| Persistência | ~80% |
| Agente WS ponta a ponta | ~70% |
| Sem GPU (degraded) | ~75% |
| Produção completa | ~65–70% |

**Falta para 100% produto:** E2E no seu Debian+GPU, login JWT, Setup.exe binário, parsers Excel/ERP robustos, fila offline persistente, observabilidade, pagamento.

Não é o máximo teórico absoluto; é **plataforma + frota + comercial**, além do escopo de Cursor/Codex (IDE na nuvem).

---

## 11. Por que Cursor/Codex não entregam isso

Escopo de IDE ≠ multi-tenant + billing + frota Windows + Tunnel. Conversas longas perdem contexto. Pouca persistência real. Pouco deploy GPU/Cloudflare/claim.

---

## 12. Próximos passos

1. `docker compose up -d --build` e validar `/health` com `db:true`
2. Cadastrar 1 agente + claim no Windows
3. Testar AGENTE-PC-* online e offline
4. Profile gpu + modelo
5. Cloudflare
6. (Opcional) EXE + login usuários

---

*ISABEL AI Local Stack v1.0.2*
