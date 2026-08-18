from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.config import settings
from app.services.llm import llm

router = APIRouter(prefix="/chat", tags=["chat"])


def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")


class ChatRequest(BaseModel):
    messages: List[dict]
    temperature: float = 0.2
    max_tokens: int = 2048


@router.post("")
async def chat(body: ChatRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    content = await llm.chat(body.messages, body.temperature, body.max_tokens)
    return {"role": "assistant", "content": content}
