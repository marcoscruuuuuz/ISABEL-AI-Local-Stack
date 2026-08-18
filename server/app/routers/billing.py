from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.db import fetchrow, execute, is_db_available

router = APIRouter(prefix="/billing", tags=["billing"])
USAGE = {}

def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")

class TokenConsume(BaseModel):
    tenant_id: str
    tokens: int
    reason: str = "chat"

@router.post("/consume")
async def consume_tokens(body: TokenConsume, authorization: str | None = Header(default=None)):
    auth(authorization)
    if is_db_available():
        await execute("INSERT INTO token_usage (tenant_id, tokens, reason) VALUES ($1,$2,$3)", body.tenant_id, body.tokens, body.reason)
        await execute("UPDATE tenants SET tokens_used = tokens_used + $1 WHERE id=$2", body.tokens, body.tenant_id)
        row = await fetchrow("SELECT tokens_used FROM tenants WHERE id=$1", body.tenant_id)
        total = int(row["tokens_used"]) if row else body.tokens
        return {"tenant_id": body.tenant_id, "consumed": body.tokens, "total_used": total, "ok": True}
    USAGE[body.tenant_id] = USAGE.get(body.tenant_id, 0) + body.tokens
    return {"tenant_id": body.tenant_id, "consumed": body.tokens, "total_used": USAGE[body.tenant_id], "ok": True}

@router.get("/summary/{tenant_id}")
async def billing_summary(tenant_id: str, authorization: str | None = Header(default=None)):
    auth(authorization)
    if is_db_available():
        row = await fetchrow("SELECT tokens_used FROM tenants WHERE id=$1", tenant_id)
        used = int(row["tokens_used"]) if row else 0
    else:
        used = USAGE.get(tenant_id, 0)
    return {"tenant_id": tenant_id, "tokens_used": used, "estimated_cost_brl": round(used / 1000 * settings.token_price_per_1k, 2)}
