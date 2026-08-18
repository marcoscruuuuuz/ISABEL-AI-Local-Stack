from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")


class TokenConsume(BaseModel):
    tenant_id: str
    tokens: int
    reason: str = "chat"


USAGE = {}


@router.post("/consume")
async def consume_tokens(body: TokenConsume, authorization: str | None = Header(default=None)):
    auth(authorization)
    key = body.tenant_id
    if key not in USAGE:
        USAGE[key] = 0
    USAGE[key] += body.tokens
    return {
        "tenant_id": body.tenant_id,
        "consumed": body.tokens,
        "total_used": USAGE[key],
        "ok": True,
    }


@router.get("/summary/{tenant_id}")
async def billing_summary(tenant_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    used = USAGE.get(tenant_id, 0)
    return {
        "tenant_id": tenant_id,
        "tokens_used": used,
        "estimated_cost_brl": round(used / 1000 * settings.token_price_per_1k, 2),
    }
