# ISABEL AI Local Stack

**Sistema comercial completo de IA local offline-first**  
Chat estilo ChatGPT + Codex · Deep Research · Agente Windows · Multi-tenant · Cloudflare Tunnel

## Hardware alvo
- RTX 5060 12GB (ou superior)
- Xeon 54 núcleos
- 64 GB DDR4
- 1 TB SSD (modelos + sistema)
- 4 TB HD (corpus / aprendizado)

## Arquitetura

```
PC Cliente (Windows)
  ISABEL-Agent.exe  ──WSS + Service Token──►  Cloudflare Access
                                                    │
                                                    ▼
                                            Cloudflare Tunnel
                                                    │
                                                    ▼
Servidor Debian (Central)
  ├── FastAPI Gateway (chat, research, agent, billing)
  ├── SGLang / vLLM (LLM)
  ├── Qdrant (vetores)
  ├── PostgreSQL (clientes, planos, tokens, auditoria)
  ├── Redis (cache / filas)
  ├── Open WebUI + Chat custom (React)
  └── Admin Dashboard
```

## Componentes principais

| Camada              | Tecnologia                          | Função                              |
|---------------------|-------------------------------------|-------------------------------------|
| LLM Serving         | SGLang (principal) + vLLM           | Inferência local rápida             |
| Vetores             | Qdrant                              | RAG + memória de longo prazo        |
| API                 | FastAPI                             | Orquestração + OpenAI-compatible    |
| Chat Web            | React + Tailwind (estilo ChatGPT)   | Interface cliente                   |
| Admin               | React                               | Planos, tokens, clientes, auditoria |
| Agent Windows       | Python → PyInstaller                | Acesso controlado a arquivos        |
| Conectividade       | Cloudflare Tunnel + Access          | Zero portas abertas                 |
| Comercial           | PostgreSQL + lógica de franquia     | Multi-tenant, billing por tokens    |

## Instalação rápida (Debian)

```bash
git clone https://github.com/marcoscruuuuuz/ISABEL-AI-Local-Stack.git /opt/isabel
cd /opt/isabel
cp .env.example .env
# Edite .env (API_TOKEN, Cloudflare, Postgres, etc.)
./install.sh
./scripts/pull_models.sh Qwen/Qwen2.5-14B-Instruct-AWQ
docker compose up -d
```

## Versão
1.0.2

## Licença
Proprietária – Innovation RP Telecom
