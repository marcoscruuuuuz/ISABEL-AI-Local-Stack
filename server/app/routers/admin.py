from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")


class TenantCreate(BaseModel):
    name: str
    email: str
    plan: str = "starter"
    seats: int = 1


PLANS = {
    "starter": {"name": "Starter", "monthly_tokens": 500_000, "price_brl": 297.0, "seats": 3},
    "pro": {"name": "Pro", "monthly_tokens": 2_000_000, "price_brl": 897.0, "seats": 10},
    "enterprise": {"name": "Enterprise", "monthly_tokens": 10_000_000, "price_brl": 2497.0, "seats": 50},
}

TENANTS = {}


@router.get("/plans")
async def list_plans(authorization: str | None = Header(default=None)):
    auth(authorization)
    return [{"id": k, **v} for k, v in PLANS.items()]


@router.post("/tenants")
async def create_tenant(body: TenantCreate, authorization: str | None = Header(default=None)):
    auth(authorization)
    tid = f"t_{len(TENANTS)+1}"
    TENANTS[tid] = {
        "id": tid,
        "name": body.name,
        "email": body.email,
        "plan": body.plan,
        "seats": body.seats,
        "tokens_used": 0,
        "tokens_quota": PLANS.get(body.plan, PLANS["starter"])["monthly_tokens"],
        "active": True,
    }
    return TENANTS[tid]


@router.get("/tenants")
async def list_tenants(authorization: str | None = Header(default=None)):
    auth(authorization)
    return list(TENANTS.values())


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if tenant_id not in TENANTS:
        raise HTTPException(404, "tenant not found")
    return TENANTS[tenant_id]


@router.get("/usage/{tenant_id}")
async def get_usage(tenant_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    t = TENANTS.get(tenant_id)
    if not t:
        raise HTTPException(404, "tenant not found")
    return {
        "tenant_id": tenant_id,
        "tokens_used": t["tokens_used"],
        "tokens_quota": t["tokens_quota"],
        "percent": round(100 * t["tokens_used"] / max(t["tokens_quota"], 1), 2),
    }
