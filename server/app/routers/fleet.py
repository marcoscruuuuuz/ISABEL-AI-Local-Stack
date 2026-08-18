"""API da frota de agentes locais (ate 100 por tenant)."""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel
from app.core.config import settings
from app.models.agents_fleet import (
    FleetAgent, FleetAgentCreate, FleetAgentUpdate, AgentStatus,
    AgentQueryRequest, AgentQueryResponse, TenantTokenUsage,
)

router = APIRouter(prefix="/fleet", tags=["fleet"])
FLEET: Dict[str, FleetAgent] = {}
NAME_INDEX: Dict[str, str] = {}
USAGE: Dict[str, TenantTokenUsage] = {}
MAX_AGENTS_PER_TENANT = 100

def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")

@router.post("/agents", response_model=FleetAgent)
async def create_agent(body: FleetAgentCreate, authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default")):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    count = sum(1 for a in FLEET.values() if a.tenant_id == tenant_id)
    if count >= MAX_AGENTS_PER_TENANT:
        raise HTTPException(400, f"Limite de {MAX_AGENTS_PER_TENANT} agentes atingido")
    key = f"{tenant_id}:{body.name}"
    if key in NAME_INDEX:
        raise HTTPException(409, f"Agente '{body.name}' ja existe")
    agent = FleetAgent(
        tenant_id=tenant_id, name=body.name, display_name=body.display_name,
        description=body.description, capabilities=body.capabilities,
        allow_paths=body.allow_paths, deny_paths=body.deny_paths,
        local_systems=body.local_systems, auto_start=body.auto_start,
        offline_capable=body.offline_capable, status=AgentStatus.PENDING,
    )
    FLEET[agent.id] = agent
    NAME_INDEX[key] = agent.id
    return agent

@router.get("/agents", response_model=List[FleetAgent])
async def list_agents(authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default"), status: Optional[AgentStatus] = None):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    agents = [a for a in FLEET.values() if a.tenant_id == tenant_id]
    if status:
        agents = [a for a in agents if a.status == status]
    return sorted(agents, key=lambda a: a.created_at, reverse=True)

@router.get("/agents/{agent_id}", response_model=FleetAgent)
async def get_agent(agent_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if agent_id not in FLEET:
        raise HTTPException(404, "agent not found")
    return FLEET[agent_id]

@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if agent_id not in FLEET:
        raise HTTPException(404, "agent not found")
    agent = FLEET.pop(agent_id)
    NAME_INDEX.pop(f"{agent.tenant_id}:{agent.name}", None)
    return {"ok": True, "deleted": agent_id}

class InstallPayload(BaseModel):
    install_key: str
    machine_id: str
    hostname: str
    version: str = "1.0.2"

@router.post("/agents/claim")
async def claim_agent(body: InstallPayload):
    agent = next((a for a in FLEET.values() if a.install_key == body.install_key), None)
    if not agent:
        raise HTTPException(404, "install_key invalida")
    agent.machine_id = body.machine_id
    agent.hostname = body.hostname
    agent.version = body.version
    agent.status = AgentStatus.ONLINE
    agent.last_seen = datetime.utcnow()
    return {
        "agent_id": agent.id, "agent_name": agent.name, "agent_token": agent.agent_token,
        "tenant_id": agent.tenant_id, "allow_paths": agent.allow_paths, "deny_paths": agent.deny_paths,
        "local_systems": agent.local_systems, "capabilities": [c.value for c in agent.capabilities],
        "model_local": agent.model_local, "auto_start": agent.auto_start,
        "server_wss": f"/ws/fleet/{agent.id}",
    }

@router.post("/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str, authorization: str | None = Header(default=None)):
    if agent_id not in FLEET:
        raise HTTPException(404, "agent not found")
    agent = FLEET[agent_id]
    token = (authorization or "").replace("Bearer ", "")
    if token != agent.agent_token:
        raise HTTPException(401, "invalid agent token")
    agent.last_seen = datetime.utcnow()
    agent.status = AgentStatus.ONLINE
    return {"ok": True, "status": "online"}

@router.post("/query", response_model=AgentQueryResponse)
async def query_agent(body: AgentQueryRequest, authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default")):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    key = f"{tenant_id}:{body.agent_name}"
    agent_id = NAME_INDEX.get(key)
    if not agent_id or agent_id not in FLEET:
        raise HTTPException(404, f"Agente '{body.agent_name}' nao encontrado")
    agent = FLEET[agent_id]
    offline = agent.status != AgentStatus.ONLINE
    return AgentQueryResponse(
        agent_id=agent.id, agent_name=agent.name, question=body.question,
        answer=f"[Agente {agent.display_name} {'OFFLINE' if offline else 'ONLINE'}] Consulta: {body.question}. Sistemas: {[s.get('label', s.get('path','')) for s in agent.local_systems] or ['workspace']}.",
        source="offline_cache" if offline else "server_pending_ws", offline=offline, latency_ms=0,
    )

@router.get("/usage", response_model=TenantTokenUsage)
async def get_usage(authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default"), period: str = Query(default="")):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    if not period:
        period = datetime.utcnow().strftime("%Y-%m")
    if tenant_id not in USAGE:
        USAGE[tenant_id] = TenantTokenUsage(tenant_id=tenant_id, period=period, tokens_used=0, tokens_quota=settings.monthly_quota_starter, cost_brl=0.0)
    return USAGE[tenant_id]

@router.get("/stats")
async def fleet_stats(authorization: str | None = Header(default=None), x_tenant_id: Optional[str] = Header(default="default")):
    auth(authorization)
    tenant_id = x_tenant_id or "default"
    agents = [a for a in FLEET.values() if a.tenant_id == tenant_id]
    return {
        "total": len(agents),
        "online": sum(1 for a in agents if a.status == AgentStatus.ONLINE),
        "offline": sum(1 for a in agents if a.status == AgentStatus.OFFLINE),
        "pending": sum(1 for a in agents if a.status == AgentStatus.PENDING),
        "limit": MAX_AGENTS_PER_TENANT,
        "remaining": MAX_AGENTS_PER_TENANT - len(agents),
    }
