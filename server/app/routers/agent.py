from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.services import agent_runtime as ag
from app.services.llm import llm
import json
import re

router = APIRouter(prefix="/agent", tags=["agent"])


def auth(authorization: str | None):
    if not authorization or authorization.replace("Bearer ", "") != settings.api_token:
        raise HTTPException(401, "unauthorized")


class AgentIn(BaseModel):
    goal: str
    max_steps: int = 8


@router.post("/run")
async def run_agent(body: AgentIn, authorization: str | None = Header(default=None)):
    auth(authorization)
    transcript = []
    try:
        system = open("/app/prompts/coding_agent.md", encoding="utf-8").read()
    except Exception:
        system = "Você é um agente de engenharia local. Trabalhe só dentro de /workspace. Responda SOMENTE com JSON."

    memory = f"GOAL: {body.goal}\nWORKSPACE ROOT: /workspace\n"

    for step in range(body.max_steps):
        thought = await llm.chat(
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": memory
                    + "\nResponda em JSON com action e args. actions: list_dir, read_file, write_file, apply_patch, run_cmd, lint_python, finish",
                },
            ],
            temperature=0.1,
        )
        transcript.append({"step": step, "model": thought})
        m = re.search(r"\{[\s\S]*\}", thought)
        if not m:
            break
        try:
            act = json.loads(m.group(0))
        except Exception:
            break
        action = act.get("action")
        args = act.get("args", {})

        try:
            if action == "list_dir":
                result = ag.list_dir(args.get("path", "."))
            elif action == "read_file":
                result = ag.read_file(args["path"])
            elif action == "write_file":
                result = ag.write_file(args["path"], args["content"])
            elif action == "apply_patch":
                result = ag.apply_patch(args["path"], args["old"], args["new"])
            elif action == "run_cmd":
                result = ag.run_cmd(args["cmd"])
            elif action == "lint_python":
                result = ag.lint_python(args["path"])
            elif action == "finish":
                return {"ok": True, "result": args.get("summary", ""), "transcript": transcript}
            else:
                result = f"ação desconhecida: {action}"
        except Exception as e:
            result = f"ERROR: {e}"

        memory += f"\nACTION {action} {args}\nRESULT:\n{result}\n"
        transcript.append({"action": action, "result": str(result)[:4000]})

    return {"ok": False, "result": "max_steps", "transcript": transcript}
