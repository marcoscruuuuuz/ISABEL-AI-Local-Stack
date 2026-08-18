from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import logging

from app.core.config import settings
from app.version import ISABEL_VERSION
from app.routers import agent, chat, research, admin, billing, multi_agent, fleet
from app.services.llm import llm
from app.services.qdrant_store import store
from app.db import get_pool, close_pool, is_db_available

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("isabel")

app = FastAPI(
    title="ISABEL AI Local Stack",
    version=ISABEL_VERSION,
    description="Chat + Deep Research + Agent + Fleet + Commercial Multi-tenant",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(research.router)
app.include_router(agent.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(multi_agent.router)
app.include_router(fleet.router)


def _auth(authorization: str | None = Header(default=None)):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")
    return True


@app.on_event("startup")
async def startup():
    logger.info(f"ISABEL AI Local Stack v{ISABEL_VERSION} starting...")
    await get_pool()
    logger.info(f"Database: {'Postgres OK' if is_db_available() else 'in-memory fallback'}")
    try:
        store.ensure(dim=1024)
        logger.info("Qdrant collection ready")
    except Exception as e:
        logger.warning(f"Qdrant init: {e}")


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": ISABEL_VERSION,
        "service": "isabel-gateway",
        "db": is_db_available(),
        "llm": settings.sglang_url,
    }


@app.get("/v1/models")
async def list_models(authorization: str | None = Header(default=None)):
    _auth(authorization)
    return {
        "object": "list",
        "data": [{"id": settings.llm_model, "object": "model", "owned_by": "isabel"}],
    }


class ChatIn(BaseModel):
    messages: List[dict]
    temperature: float = 0.2
    max_tokens: int = 2048
    stream: bool = False


@app.post("/v1/chat/completions")
async def chat_completions(body: ChatIn, authorization: str | None = Header(default=None)):
    _auth(authorization)
    try:
        content = await llm.chat(body.messages, body.temperature, body.max_tokens)
    except Exception as e:
        content = (
            f"[ISABEL modo degradado] LLM indisponivel ({settings.sglang_url}): {e}. "
            "Suba o profile gpu ou configure SGLANG_URL. "
            "Para dados de PC use AGENTE-PC-* no chat."
        )
    return {
        "id": "chatcmpl-isabel",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "model": settings.llm_model,
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.websocket("/ws/agent/{machine_id}")
async def agent_ws(websocket: WebSocket, machine_id: str):
    await websocket.accept()
    logger.info(f"Agent connected: {machine_id}")
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "heartbeat":
                await websocket.send_json({"type": "pong", "ts": data.get("ts")})
            elif data.get("type") == "task_result":
                await websocket.send_json({"type": "ack", "task_id": data.get("task_id")})
            else:
                await websocket.send_json({"type": "error", "message": "unknown type"})
    except WebSocketDisconnect:
        logger.info(f"Agent disconnected: {machine_id}")


@app.websocket("/ws/fleet/{agent_id}")
async def fleet_ws(websocket: WebSocket, agent_id: str):
    await websocket.accept()
    fleet.WS_CONNECTIONS[agent_id] = websocket
    logger.info(f"Fleet agent connected: {agent_id}")
    try:
        ag = await fleet._get_agent(agent_id)
        if ag:
            from app.models.agents_fleet import AgentStatus
            from datetime import datetime
            ag.status = AgentStatus.ONLINE
            ag.last_seen = datetime.utcnow()
            await fleet._save_agent(ag)
    except Exception as e:
        logger.warning(f"fleet online update: {e}")
    try:
        while True:
            data = await websocket.receive_json()
            t = data.get("type")
            if t in ("heartbeat", "ping"):
                await websocket.send_json({"type": "pong", "ts": data.get("ts")})
            elif t == "task_result":
                task_id = data.get("task_id")
                fut = fleet.PENDING.pop(task_id, None)
                if fut and not fut.done():
                    fut.set_result(data)
                await websocket.send_json({"type": "ack", "task_id": task_id})
            else:
                await websocket.send_json({"type": "ack"})
    except WebSocketDisconnect:
        logger.info(f"Fleet agent disconnected: {agent_id}")
    finally:
        if fleet.WS_CONNECTIONS.get(agent_id) is websocket:
            fleet.WS_CONNECTIONS.pop(agent_id, None)
        try:
            ag = await fleet._get_agent(agent_id)
            if ag:
                from app.models.agents_fleet import AgentStatus
                ag.status = AgentStatus.OFFLINE
                await fleet._save_agent(ag)
        except Exception:
            pass
