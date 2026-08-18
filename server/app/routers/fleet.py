"""API da frota de agentes locais (ate 100 por tenant). Persistencia Postgres + fallback memoria + WS live."""
from __future__ import annotations
import asyncio, json, uuid
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from app.core.config import settings
from app.models.agents_fleet import (
    FleetAgent, FleetAgentCreate, AgentStatus,
    AgentQueryRequest, AgentQueryResponse, TenantTokenUsage, AgentCapability,
)
from app.db import fetch, fetchrow, execute, is_db_available

router = APIRouter(prefix="/fleet", tags=["fleet"])
FLEET: Dict[str, FleetAgent] = {}
NAME_INDEX: Dict[str, str] = {}
USAGE: Dict[str, TenantTokenUsage] = {}
WS_CONNECTIONS: Dict = {}
PENDING: Dict[str, asyncio.Future] = {}
MAX_AGENTS_PER_TENANT = 100

def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")

def _row_to_agent(row: dict) -> FleetAgent:
    caps = row.get("capabilities") or []
    if isinstance(caps, str):
        caps = json.loads(caps)
    for key in ("allow_paths", "deny_paths", "local_systems"):
        if isinstance(row.get(key), str):
            row[key] = json.loads(row[key])
    return FleetAgent(
        id=row["id"], tenant_id=row["tenant_id"], name=row["name"],
        display_name=row["display_name"], description=row.get("description"),
        status=AgentStatus(row.get("status") or "pending"),
        machine_id=row.get("machine_id"), hostname=row.get("hostname"),
        version=row.get("version") or "1.0.2",
        model_local=row.get("model_local") or "Qwen2.5-1.5B-Instruct.Q4_K_M",
        capabilities=[AgentCapability(c) if not isinstance(c, AgentCapability) else c for c in caps],
        allow_paths=row.get("allow_paths") or [], deny_paths=row.get("deny_paths") or [],
        local_systems=row.get("local_systems") or [],
        auto_start=bool(row.get("auto_start", True)), offline_capable=bool(row.get("offline_capable", True)),
        agent_token=row["agent_token"], install_key=row["install_key"],
        last_seen=row.get("last_seen"), tokens_used=int(row.get("tokens_used") or 0),
        created_at=row.get("created_at") or datetime.utcnow(),
        updated_at=row.get("updated_at") or datetime.utcnow(),
    )

async def _save_agent(agent: FleetAgent):
    if is_db_available():
        await execute(
            """INSERT INTO fleet_agents (
                id, tenant_id, name, display_name, description, status,
                machine_id, hostname, version, model_local, capabilities,
                allow_paths, deny_paths, local_systems, auto_start, offline_capable,
                agent_token, install_key, last_seen, tokens_used, created_at, updated_at
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12::jsonb,$13::jsonb,$14::jsonb,$15,$16,$17,$18,$19,$20,$21,$22)
            ON CONFLICT (id) DO UPDATE SET
                display_name=EXCLUDED.display_name, description=EXCLUDED.description,
                status=EXCLUDED.status, machine_id=EXCLUDED.machine_id, hostname=EXCLUDED.hostname,
                version=EXCLUDED.version, capabilities=EXCLUDED.capabilities,
                allow_paths=EXCLUDED.allow_paths, deny_paths=EXCLUDED.deny_paths,
                local_systems=EXCLUDED.local_systems, last_seen=EXCLUDED.last_seen,
                tokens_used=EXCLUDED.tokens_used, updated_at=EXCLUDED.updated_at""",
            agent.id, agent.tenant_id, agent.name, agent.display_name, agent.description,
            agent.status.value, agent.machine_id, agent.hostname, agent.version, agent.model_local,
            json.dumps([c.value for c in agent.capabilities]),
            json.dumps(agent.allow_paths), json.dumps(agent.deny_paths),
            json.dumps(agent.local_systems), agent.auto_start, agent.offline_capable,
            agent.agent_token, agent.install_key, agent.last_seen, agent.tokens_used,
            agent.created_at, agent.updated_at,
        )
    FLEET[agent.id] = agent
    NAME_INDEX[f"{agent.tenant_id}:{agent.name}"] = agent.id

async def _get_agent(agent_id: str) -> Optional[FleetAgent]:
    if is_db_available():
        row = await fetchrow("SELECT * FROM fleet_agents WHERE id=$1", agent_id)
        if row:
            return _row_to_agent(row)
    return FLEET.get(agent_id)

async def _get_by_name(tenant_id: str, name: str) -> Optional[FleetAgent]:
    if is_db_available():
        row = await fetchrow("SELECT * FROM fleet_agents WHERE tenant_id=$1 AND name=$2", tenant_id, name)
        if row:
            return _row_to_agent(row)
    aid = NAME_INDEX.get(f"{tenant_id}:{name}")
    return FLEET.get(aid) if aid else None

async def _list_agents(tenant_id: str, status: Optional[str] = None) -> List[FleetAgent]:
    if is_db_available():
        if status:
            rows = await fetch("SELECT * FROM fleet_agents WHERE tenant_id=$1 AND status=$2 ORDER BY created_at DESC", tenant_id, status)
        else:
            rows = await fetch("SELECT * FROM fleet_agents WHERE tenant_id=$1 ORDER BY created_at DESC", tenant_id)
        return [_row_to_agent(r) for r in rows]
    agents = [a for a in FLEET.values() if a.tenant_id == tenant_id]
    if status:
        agents = [a for a in agents if a.status.value == status]
    return sorted(agents, key=lambda a: a.created_at, reverse=True)

@router.post("/agents", response_model=FleetAgent)
async def create_agent(body: FleetAgentCreate, authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default")):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    if len(await _list_agents(tenant_id)) >= MAX_AGENTS_PER_TENANT:
        raise HTTPException(400, f"Limite de {MAX_AGENTS_PER_TENANT} agentes atingido")
    if await _get_by_name(tenant_id, body.name):
        raise HTTPException(409, f"Agente '{body.name}' ja existe")
    agent = FleetAgent(tenant_id=tenant_id, name=body.name, display_name=body.display_name,
        description=body.description, capabilities=body.capabilities, allow_paths=body.allow_paths,
        deny_paths=body.deny_paths, local_systems=body.local_systems, auto_start=body.auto_start,
        offline_capable=body.offline_capable, status=AgentStatus.PENDING)
    await _save_agent(agent)
    return agent

@router.get("/agents", response_model=List[FleetAgent])
async def list_agents(authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default"), status: Optional[AgentStatus] = None):
    auth(authorization)
    return await _list_agents(x_tenant_id or "default", status.value if status else None)

@router.get("/agents/{agent_id}", response_model=FleetAgent)
async def get_agent(agent_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    return agent

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    if is_db_available():
        await execute("DELETE FROM fleet_agents WHERE id=$1", agent_id)
    FLEET.pop(agent_id, None)
    NAME_INDEX.pop(f"{agent.tenant_id}:{agent.name}", None)
    return {"ok": True, "deleted": agent_id}

class InstallPayload(BaseModel):
    install_key: str
    machine_id: str
    hostname: str
    version: str = "1.0.2"

@router.post("/agents/claim")
async def claim_agent(body: InstallPayload):
    agent = None
    if is_db_available():
        row = await fetchrow("SELECT * FROM fleet_agents WHERE install_key=$1", body.install_key)
        if row:
            agent = _row_to_agent(row)
    if not agent:
        agent = next((a for a in FLEET.values() if a.install_key == body.install_key), None)
    if not agent:
        raise HTTPException(404, "install_key invalida")
    agent.machine_id = body.machine_id
    agent.hostname = body.hostname
    agent.version = body.version
    agent.status = AgentStatus.ONLINE
    agent.last_seen = datetime.utcnow()
    agent.updated_at = datetime.utcnow()
    await _save_agent(agent)
    return {
        "agent_id": agent.id, "agent_name": agent.name, "agent_token": agent.agent_token,
        "tenant_id": agent.tenant_id, "allow_paths": agent.allow_paths, "deny_paths": agent.deny_paths,
        "local_systems": agent.local_systems, "capabilities": [c.value for c in agent.capabilities],
        "model_local": agent.model_local, "auto_start": agent.auto_start,
        "server_wss": f"/ws/fleet/{agent.id}",
    }

@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str, authorization: str | None = Header(default=None)):
    agent = await _get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "agent not found")
    if (authorization or "").replace("Bearer ", "") != agent.agent_token:
        raise HTTPException(401, "invalid agent token")
    agent.last_seen = datetime.utcnow()
    agent.status = AgentStatus.ONLINE
    await _save_agent(agent)
    return {"ok": True, "status": "online"}

@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(body: AgentQueryRequest, authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default")):
    auth(authorization)
    agent = await _get_by_name(x_tenant_id or "default", body.agent_name)
    if not agent:
        raise HTTPException(404, f"Agente '{body.agent_name}' nao encontrado")
    query_id = f"q_{uuid.uuid4().hex[:12]}"
    ws = WS_CONNECTIONS.get(agent.id)
    if ws is not None:
        fut = asyncio.get_event_loop().create_future()
        PENDING[query_id] = fut
        try:
            await ws.send_json({"type": "query", "task_id": query_id, "question": body.question, "context": body.context or {}})
            result = await asyncio.wait_for(fut, timeout=min(body.timeout_seconds, 90))
            return AgentQueryResponse(
                agent_id=agent.id, agent_name=agent.name, question=body.question,
                answer=result.get("result") or result.get("answer") or str(result),
                source=result.get("source", "local_2b"), offline=False, latency_ms=0,
                evidence=result.get("evidence"),
            )
        except asyncio.TimeoutError:
            PENDING.pop(query_id, None)
        except Exception:
            PENDING.pop(query_id, None)
    if agent.offline_capable:
        return AgentQueryResponse(
            agent_id=agent.id, agent_name=agent.name, question=body.question,
            answer=f"[Agente {agent.display_name} OFFLINE] Consulta: '{body.question}'. Reconecte o agent Windows 2B.",
            source="offline_cache", offline=True, latency_ms=0,
        )
    raise HTTPException(503, f"Agente '{body.agent_name}' offline")

@router.get("/usage", response_model=TenantTokenUsage)
async def get_usage(authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default"), period: str = Query(default="")):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    if not period:
        period = datetime.utcnow().strftime("%Y-%m")
    tokens_used, quota = 0, settings.monthly_quota_starter
    if is_db_available():
        row = await fetchrow("SELECT COALESCE(SUM(tokens),0) AS total FROM token_usage WHERE tenant_id=$1 AND to_char(created_at,'YYYY-MM')=$2", tenant_id, period)
        tokens_used = int(row["total"]) if row else 0
        trow = await fetchrow("SELECT tokens_quota FROM tenants WHERE id=$1", tenant_id)
        if trow:
            quota = int(trow["tokens_quota"])
    else:
        u = USAGE.get(tenant_id)
        tokens_used = u.tokens_used if u else 0
    return TenantTokenUsage(tenant_id=tenant_id, period=period, tokens_used=tokens_used, tokens_quota=quota, cost_brl=round(tokens_used/1000*settings.token_price_per_1k, 2))

@router.get("/stats")
async def fleet_stats(authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default")):
    auth(authorization)
    agents = await _list_agents(x_tenant_id or "default")
    return {
        "total": len(agents),
        "online": sum(1 for a in agents if a.status == AgentStatus.ONLINE or a.id in WS_CONNECTIONS),
        "offline": sum(1 for a in agents if a.status == AgentStatus.OFFLINE),
        "pending": sum(1 for a in agents if a.status == AgentStatus.PENDING),
        "limit": MAX_AGENTS_PER_TENANT,
        "remaining": MAX_AGENTS_PER_TENANT - len(agents),
        "db": is_db_available(),
    }

@router.get("/health-detail")
async def fleet_health():
    return {"db": is_db_available(), "agents_memory": len(FLEET), "ws_connected": list(WS_CONNECTIONS.keys()), "pending_queries": len(PENDING)}
