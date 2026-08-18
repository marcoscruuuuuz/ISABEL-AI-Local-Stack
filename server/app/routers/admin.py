from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.db import fetch, fetchrow, execute, is_db_available

router = APIRouter(prefix="/admin", tags=["admin"])
TENANTS = {}
PLANS = {
    "starter": {"name": "Starter", "monthly_tokens": 500_000, "price_brl": 297.0, "seats": 3},
    "pro": {"name": "Pro", "monthly_tokens": 2_000_000, "price_brl": 897.0, "seats": 10},
    "enterprise": {"name": "Enterprise", "monthly_tokens": 10_000_000, "price_brl": 2497.0, "seats": 50},
}

def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")

class TenantCreate(BaseModel):
    name: str
    email: str
    plan: str = "starter"
    seats: int = 1

@router.get("/plans")
async def list_plans(authorization: str | None = Header(default=None)):
    auth(authorization)
    if is_db_available():
        rows = await fetch("SELECT id, name, monthly_tokens, price_brl, seats FROM plans ORDER BY price_brl")
        if rows:
            return rows
    return [{"id": k, **v} for k, v in PLANS.items()]

@router.post("/tenants")
async def create_tenant(body: TenantCreate, authorization: str | None = Header(default=None)):
    auth(authorization)
    quota = PLANS.get(body.plan, PLANS["starter"])["monthly_tokens"]
    if is_db_available():
        import uuid
        tid = f"t_{uuid.uuid4().hex[:10]}"
        await execute("INSERT INTO tenants (id, name, email, plan, seats, tokens_quota) VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (email) DO NOTHING", tid, body.name, body.email, body.plan, body.seats, quota)
        row = await fetchrow("SELECT * FROM tenants WHERE email=$1", body.email)
        if row:
            return dict(row)
        return {"id": tid, "name": body.name, "email": body.email, "plan": body.plan, "seats": body.seats, "tokens_quota": quota, "tokens_used": 0, "active": True}
    tid = f"t_{len(TENANTS)+1}"
    TENANTS[tid] = {"id": tid, "name": body.name, "email": body.email, "plan": body.plan, "seats": body.seats, "tokens_used": 0, "tokens_quota": quota, "active": True}
    return TENANTS[tid]

@router.get("/tenants")
async def list_tenants(authorization: str | None = Header(default=None)):
    auth(authorization)
    if is_db_available():
        return await fetch("SELECT * FROM tenants ORDER BY created_at DESC")
    return list(TENANTS.values())

@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if is_db_available():
        row = await fetchrow("SELECT * FROM tenants WHERE id=$1", tenant_id)
        if not row:
            raise HTTPException(404, "tenant not found")
        return dict(row)
    if tenant_id not in TENANTS:
        raise HTTPException(404, "tenant not found")
    return TENANTS[tenant_id]

@router.get("/usage/{tenant_id}")
async def get_usage(tenant_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if is_db_available():
        t = await fetchrow("SELECT * FROM tenants WHERE id=$1", tenant_id)
        if not t:
            raise HTTPException(404, "tenant not found")
        return {"tenant_id": tenant_id, "tokens_used": int(t["tokens_used"] or 0), "tokens_quota": int(t["tokens_quota"] or 1), "percent": round(100 * int(t["tokens_used"] or 0) / max(int(t["tokens_quota"] or 1), 1), 2)}
    t = TENANTS.get(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    return {"tenant_id": tenant_id, "tokens_used": t["tokens_used"], "tokens_quota": t["tokens_quota"], "percent": round(100 * t["tokens_used"] / max(t["tokens_quota"], 1), 2)}
