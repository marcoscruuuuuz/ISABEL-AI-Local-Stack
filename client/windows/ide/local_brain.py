#!/usr/bin/env python3
"""ISABEL IDE Brain Client - modelo 2B local + escala para servidor."""
from __future__ import annotations
import os, json, httpx
from typing import List, Dict, Any, Optional

LOCAL_URL = os.getenv("ISABEL_LOCAL_URL", "http://127.0.0.1:11434")
SERVER_API = os.getenv("ISABEL_API_URL", "https://ai.seudominio.com.br")
API_TOKEN = os.getenv("API_TOKEN", "")
PREFER_LOCAL = os.getenv("ISABEL_PREFER_LOCAL_2B", "true").lower() == "true"

class LocalBrain:
    def __init__(self, base_url: str = LOCAL_URL):
        self.base = base_url.rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def is_available(self) -> bool:
        try:
            r = self.client.get(f"{self.base}/health", timeout=2.0)
            return r.status_code == 200
        except Exception:
            try:
                r = self.client.get(f"{self.base}/api/tags", timeout=2.0)
                return r.status_code == 200
            except Exception:
                return False

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2, max_tokens: int = 1024) -> str:
        payload = {"model": "isabel-2b", "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": False}
        try:
            r = self.client.post(f"{self.base}/v1/chat/completions", json=payload)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
        r = self.client.post(f"{self.base}/api/chat", json={"model": "isabel-2b", "messages": messages, "stream": False, "options": {"temperature": temperature, "num_predict": max_tokens}})
        r.raise_for_status()
        return r.json()["message"]["content"]

    def should_escalate(self, goal: str) -> bool:
        heavy = ["refatorar tudo", "arquitetura", "deep research", "multi arquivo", "todo o projeto", "segurança completa", "migrar banco", "performance"]
        g = goal.lower()
        return any(k in g for k in heavy) or len(goal) > 400

def hybrid_run(goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    brain = LocalBrain()
    context = context or {}
    if PREFER_LOCAL and brain.is_available() and not brain.should_escalate(goal):
        try:
            content = brain.chat([{"role": "system", "content": "Você é o IDE Brain local do ISABEL (modelo 2B). Responda de forma prática."}, {"role": "user", "content": f"GOAL: {goal}\nCONTEXT: {json.dumps(context)}"}])
            return {"ok": True, "mode": "offline_local", "engine": "ide_brain_2b", "result": content}
        except Exception:
            pass
    try:
        with httpx.Client(timeout=180.0) as client:
            r = client.post(f"{SERVER_API}/multi-agent/run", headers={"Authorization": f"Bearer {API_TOKEN}", "Content-Type": "application/json"}, json={"goal": goal, "mode": "multi_agent", "context": context, "prefer_local_2b": False})
            r.raise_for_status()
            data = r.json()
            data["engine"] = "server_multi_agent"
            return data
    except Exception as e:
        return {"ok": False, "mode": "failed", "error": str(e)}

if __name__ == "__main__":
    import sys
    goal = " ".join(sys.argv[1:]) or "Explique o que você consegue fazer offline"
    print(json.dumps(hybrid_run(goal), ensure_ascii=False, indent=2))
