"""
Endpoint de execução multi-agente do ISABEL.
"""

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.services.agents.supervisor import plan_task, execute_step

router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])


def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")


class MultiAgentRequest(BaseModel):
    goal: str
    context: Optional[Dict[str, Any]] = None
    mode: str = Field(default="multi_agent", description="multi_agent | single | research | offline_local")
    max_steps: int = 12
    prefer_local_2b: bool = False


@router.post("/run")
async def run_multi_agent(body: MultiAgentRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    plan = await plan_task(body.goal, body.context or {})
    plan["mode"] = body.mode
    plan["constraints"]["max_steps"] = body.max_steps

    if body.prefer_local_2b or body.mode == "offline_local":
        return {
            "ok": True,
            "mode": "offline_local",
            "message": "Plano gerado. Execute localmente com o IDE Brain 2B.",
            "plan": plan,
            "results": [],
        }

    memory = f"GOAL: {body.goal}\n"
    results: List[Dict[str, Any]] = []
    completed_steps = set()
    steps = plan.get("steps", [])[: body.max_steps]

    for step in steps:
        depends = step.get("depends_on") or []
        if not all(d in completed_steps for d in depends):
            continue
        result = await execute_step(step, memory, (body.context or {}).get("files"))
        results.append(result)
        memory += f"\n[{result['agent']}] {result['action']}:\n{result['result'][:1500]}\n"
        completed_steps.add(step.get("step_id"))

    return {
        "ok": True,
        "mode": "multi_agent",
        "plan": plan,
        "results": results,
        "final_memory": memory[-8000:],
    }


@router.post("/plan")
async def only_plan(body: MultiAgentRequest, authorization: str | None = Header(default=None)):
    auth(authorization)
    plan = await plan_task(body.goal, body.context or {})
    return plan
