#!/usr/bin/env python3
"""ISABEL Fleet Agent (Windows) - modelo 2B local + conexao a ISABEL central."""
from __future__ import annotations
import os, sys, json, time, pathlib, asyncio, logging, platform
from typing import Any, Dict, List
from datetime import datetime

ISABEL_VERSION = os.getenv("ISABEL_VERSION", "1.0.2")
AGENT_ID = os.getenv("ISABEL_AGENT_ID", "")
AGENT_NAME = os.getenv("ISABEL_AGENT_NAME", "AGENTE-PC-local")
AGENT_TOKEN = os.getenv("ISABEL_AGENT_TOKEN", "")
SERVER_WSS = os.getenv("ISABEL_SERVER_WSS", "wss://ai.seudominio.com.br/ws/fleet")
SERVER_API = os.getenv("ISABEL_API_URL", "https://ai.seudominio.com.br")
LOCAL_BRAIN_URL = os.getenv("ISABEL_LOCAL_URL", "http://127.0.0.1:11434")
ALLOW_PATHS = [p.strip() for p in os.getenv("ISABEL_ALLOW_PATHS", r"C:\Projetos;C:\Sistemas").split(";") if p.strip()]
DENY_PATHS = [p.strip() for p in os.getenv("ISABEL_DENY_PATHS", r"C:\Windows;C:\Program Files").split(";") if p.strip()]
LOCAL_SYSTEMS = json.loads(os.getenv("ISABEL_LOCAL_SYSTEMS", "[]"))
CACHE_FILE = os.getenv("ISABEL_CACHE_FILE", str(pathlib.Path.home() / ".isabel" / f"cache_{AGENT_NAME}.json"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger(AGENT_NAME)

try:
    import websockets
    import httpx
except ImportError:
    print("pip install websockets httpx")
    sys.exit(1)

class AgentError(Exception):
    pass

def is_allowed(path: str) -> bool:
    p = str(pathlib.Path(path).resolve()).lower()
    for d in DENY_PATHS:
        if p.startswith(d.lower().replace("%userprofile%", os.path.expanduser("~").lower())):
            return False
    for a in ALLOW_PATHS:
        expanded = a.replace("%USERPROFILE%", os.path.expanduser("~"))
        if p.startswith(expanded.lower()):
            return True
    return False

def read_local_file(path: str, max_bytes: int = 200_000) -> str:
    if not is_allowed(path):
        raise AgentError(f"Caminho nao permitido: {path}")
    return pathlib.Path(path).read_bytes()[:max_bytes].decode("utf-8", errors="replace")

def query_local_systems(question: str) -> Dict[str, Any]:
    evidence, snippets = [], []
    for sysinfo in LOCAL_SYSTEMS:
        path = sysinfo.get("path", "")
        label = sysinfo.get("label", path)
        try:
            if path and is_allowed(path) and pathlib.Path(path).exists():
                text = read_local_file(path, max_bytes=50_000)
                today = datetime.now().strftime("%Y-%m-%d")
                today_br = datetime.now().strftime("%d/%m/%Y")
                lines = [ln for ln in text.splitlines() if today in ln or today_br in ln or "R$" in ln]
                sample = "\n".join(lines[:30]) if lines else text[:1500]
                evidence.append({"source": path, "label": label, "snippet": sample[:2000]})
                snippets.append(f"[{label}]\n{sample[:1000]}")
        except Exception as e:
            evidence.append({"source": path, "label": label, "error": str(e)})
    return {"evidence": evidence, "context_text": "\n\n".join(snippets)[:8000]}

async def local_brain_answer(question: str, context_text: str) -> str:
    system = f"Voce e o agente local {AGENT_NAME} do ISABEL. Responda APENAS com base nas evidencias locais. Seja objetivo."
    user = f"Pergunta: {question}\n\nEvidencias:\n{context_text or '(nenhuma)'}"
    payload = {"model": "isabel-2b", "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}], "temperature": 0.1, "max_tokens": 800, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(f"{LOCAL_BRAIN_URL}/v1/chat/completions", json=payload)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            r = await client.post(f"{LOCAL_BRAIN_URL}/api/chat", json={"model": "isabel-2b", "messages": payload["messages"], "stream": False})
            if r.status_code == 200:
                return r.json()["message"]["content"]
    except Exception as e:
        log.warning(f"Brain 2B indisponivel: {e}")
    return f"[sem modelo 2B] Evidencias:\n{context_text[:2000]}" if context_text else "[sem modelo e sem evidencias]"

async def process_question(question: str) -> Dict[str, Any]:
    local = query_local_systems(question)
    answer = await local_brain_answer(question, local["context_text"])
    return {"answer": answer, "evidence": local["evidence"], "source": "local_2b", "offline": False}

async def heartbeat_loop():
    if not AGENT_ID or not AGENT_TOKEN:
        return
    url = f"{SERVER_API}/fleet/agents/{AGENT_ID}/heartbeat"
    while True:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                await client.post(url, headers={"Authorization": f"Bearer {AGENT_TOKEN}"})
        except Exception:
            pass
        await asyncio.sleep(30)

async def wss_loop():
    if not AGENT_ID:
        log.error("ISABEL_AGENT_ID nao definido. Execute claim primeiro.")
        return
    url = f"{SERVER_WSS}/{AGENT_ID}"
    headers = {"Authorization": f"Bearer {AGENT_TOKEN}"} if AGENT_TOKEN else {}
    log.info(f"{AGENT_NAME} v{ISABEL_VERSION} conectando em {url}")
    while True:
        try:
            async with websockets.connect(url, additional_headers=headers or None, ping_interval=20) as ws:
                log.info("Conectado a ISABEL central")
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=60)
                        data = json.loads(msg)
                        if data.get("type") == "query":
                            result = await process_question(data.get("question", ""))
                            await ws.send(json.dumps({"type": "task_result", "task_id": data.get("task_id", ""), "agent_name": AGENT_NAME, "result": result["answer"], "evidence": result["evidence"], "source": result["source"]}))
                        elif data.get("type") == "ping":
                            await ws.send(json.dumps({"type": "pong", "ts": time.time()}))
                    except asyncio.TimeoutError:
                        await ws.send(json.dumps({"type": "heartbeat", "agent_id": AGENT_ID, "ts": time.time()}))
        except Exception as e:
            log.warning(f"Desconectado: {e}. Reconectando em 10s...")
            await asyncio.sleep(10)

async def main():
    log.info(f"Iniciando {AGENT_NAME} | model local 2B | offline-first")
    await asyncio.gather(heartbeat_loop(), wss_loop())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Agent finalizado.")
