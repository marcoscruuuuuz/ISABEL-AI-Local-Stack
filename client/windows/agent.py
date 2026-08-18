#!/usr/bin/env python3
"""
ISABEL Agent Windows
- Conexão outbound-only via WSS + Cloudflare Access Service Token
- Acesso controlado a arquivos (allowlist)
- Heartbeat + execução de tarefas
- Sem servidor escutando no PC do cliente
"""

import os
import sys
import json
import time
import pathlib
import asyncio
import logging
import platform
from typing import Optional, List

ISABEL_VERSION = os.getenv("ISABEL_VERSION", "1.0.2")

try:
    import websockets
    import httpx
except ImportError:
    print("Instale: pip install websockets httpx")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("isabel-agent")

SERVER_WSS = os.getenv("ISABEL_SERVER_WSS", "wss://ai.seudominio.com.br/ws/agent")
MACHINE_ID = os.getenv("ISABEL_MACHINE_ID", platform.node())
CF_CLIENT_ID = os.getenv("CF_ACCESS_CLIENT_ID", "")
CF_CLIENT_SECRET = os.getenv("CF_ACCESS_CLIENT_SECRET", "")
ALLOW_PATHS = [
    p.strip() for p in os.getenv("ISABEL_ALLOW_PATHS", r"C:\\Users\\Public\\Documents;C:\\Projetos").split(";")
    if p.strip()
]
DENY_PATHS = [
    p.strip() for p in os.getenv("ISABEL_DENY_PATHS", r"C:\\Windows;C:\\Program Files").split(";")
    if p.strip()
]
ALLOW_SHELL = os.getenv("ISABEL_ALLOW_SHELL", "false").lower() == "true"
MAX_EDIT_BYTES = int(os.getenv("ISABEL_MAX_EDIT_BYTES", "2000000"))


class AgentError(Exception):
    pass


def is_allowed(path: str) -> bool:
    p = pathlib.Path(path).resolve()
    for d in DENY_PATHS:
        if str(p).lower().startswith(d.lower()):
            return False
    for a in ALLOW_PATHS:
        if str(p).lower().startswith(a.lower()):
            return True
    return False


def list_dir(path: str = ".") -> List[str]:
    if not is_allowed(path):
        raise AgentError("Caminho não permitido")
    p = pathlib.Path(path)
    return sorted([x.name + ("/" if x.is_dir() else "") for x in p.iterdir()])


def read_file(path: str, max_bytes: int = 200_000) -> str:
    if not is_allowed(path):
        raise AgentError("Caminho não permitido")
    data = pathlib.Path(path).read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def write_file(path: str, content: str) -> str:
    if not is_allowed(path):
        raise AgentError("Caminho não permitido")
    if len(content.encode()) > MAX_EDIT_BYTES:
        raise AgentError("Arquivo excede limite")
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"WROTE {p}"


async def run_agent():
    headers = {}
    if CF_CLIENT_ID and CF_CLIENT_SECRET:
        headers["CF-Access-Client-Id"] = CF_CLIENT_ID
        headers["CF-Access-Client-Secret"] = CF_CLIENT_SECRET

    url = f"{SERVER_WSS}/{MACHINE_ID}"
    log.info(f"ISABEL Agent v{ISABEL_VERSION} iniciando...")
    log.info(f"Conectando em {url}")
    log.info(f"Machine ID: {MACHINE_ID}")
    log.info(f"Allow paths: {ALLOW_PATHS}")

    while True:
        try:
            async with websockets.connect(url, extra_headers=headers, ping_interval=20) as ws:
                log.info("Conectado ao servidor ISABEL")
                while True:
                    await ws.send(json.dumps({"type": "heartbeat", "ts": time.time(), "version": ISABEL_VERSION}))
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)
                        if data.get("type") == "task":
                            task_id = data.get("task_id")
                            action = data.get("action")
                            args = data.get("args", {})
                            result = None
                            error = None
                            try:
                                if action == "list_dir":
                                    result = list_dir(args.get("path", "."))
                                elif action == "read_file":
                                    result = read_file(args["path"])
                                elif action == "write_file":
                                    result = write_file(args["path"], args["content"])
                                else:
                                    error = f"Ação não suportada: {action}"
                            except Exception as e:
                                error = str(e)
                            await ws.send(json.dumps({
                                "type": "task_result",
                                "task_id": task_id,
                                "result": result,
                                "error": error,
                            }))
                        elif data.get("type") == "pong":
                            pass
                    except asyncio.TimeoutError:
                        continue
        except Exception as e:
            log.warning(f"Desconectado: {e}. Reconectando em 10s...")
            await asyncio.sleep(10)


if __name__ == "__main__":
    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        log.info("Agent finalizado.")
