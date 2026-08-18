"""
ISABEL Multi-Agent Supervisor
Orquestra os agentes especializados e produz um plano de execução (Task Graph).
"""

from __future__ import annotations
import json
import uuid
from typing import Any, Dict, List, Optional
from app.services.llm import llm
from app.core.config import settings

SUPERVISOR_SYSTEM = """Você é o Supervisor do sistema ISABEL Multi-Agent.
Sua única saída deve ser um JSON válido com o plano de execução.

Agentes disponíveis:
- architect: planeja arquitetura e passos de alto nível
- coder: escreve e edita código
- reviewer: revisa qualidade e estilo
- debugger: analisa erros e logs
- researcher: faz deep research no corpus local
- security: verifica segurança e secrets

Formato de resposta OBRIGATÓRIO:
{
  "task_id": "uuid",
  "goal": "...",
  "mode": "multi_agent",
  "steps": [
    {
      "step_id": 1,
      "agent": "architect|coder|reviewer|debugger|researcher|security",
      "action": "descrição curta",
      "depends_on": [],
      "parallel": false
    }
  ],
  "constraints": {
    "max_steps": 12,
    "require_approval": ["write_file", "run_cmd"]
  }
}
"""


async def plan_task(goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    context = context or {}
    user_msg = f"GOAL: {goal}\n\nCONTEXT: {json.dumps(context, ensure_ascii=False)}"

    raw = await llm.chat(
        [
            {"role": "system", "content": SUPERVISOR_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=1500,
    )

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        plan = json.loads(raw[start:end])
    except Exception:
        plan = {
            "task_id": str(uuid.uuid4()),
            "goal": goal,
            "mode": "multi_agent",
            "steps": [
                {"step_id": 1, "agent": "architect", "action": "Analisar e planejar", "depends_on": [], "parallel": False},
                {"step_id": 2, "agent": "coder", "action": "Implementar mudanças", "depends_on": [1], "parallel": False},
                {"step_id": 3, "agent": "reviewer", "action": "Revisar código", "depends_on": [2], "parallel": False},
            ],
            "constraints": {
                "max_steps": 12,
                "require_approval": ["write_file", "run_cmd"],
            },
        }

    if "task_id" not in plan:
        plan["task_id"] = str(uuid.uuid4())
    plan["goal"] = goal
    return plan


async def execute_step(step: Dict[str, Any], memory: str, workspace_files: List[str] = None) -> Dict[str, Any]:
    agent_name = step.get("agent", "coder")
    action = step.get("action", "")

    agent_prompts = {
        "architect": "Você é o Architect do ISABEL. Analise o objetivo e proponha a melhor estrutura. Responda em markdown curto.",
        "coder": "Você é o Coder do ISABEL. Produza código ou patches precisos. Prefira apply_patch.",
        "reviewer": "Você é o Reviewer do ISABEL. Aponte problemas de qualidade, bugs e melhorias.",
        "debugger": "Você é o Debugger do ISABEL. Identifique a causa raiz e como reproduzir o erro.",
        "researcher": "Você é o Researcher do ISABEL. Use apenas evidências locais. Cite fontes.",
        "security": "Você é o Security Agent do ISABEL. Procure secrets, path traversal, injection e permissões inseguras.",
    }

    system = agent_prompts.get(agent_name, agent_prompts["coder"])
    user = f"Ação: {action}\n\nMemória da tarefa:\n{memory}\n\nArquivos em contexto: {workspace_files or []}"

    content = await llm.chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.15,
        max_tokens=2000,
    )

    return {
        "step_id": step.get("step_id"),
        "agent": agent_name,
        "action": action,
        "result": content,
        "status": "completed",
    }
