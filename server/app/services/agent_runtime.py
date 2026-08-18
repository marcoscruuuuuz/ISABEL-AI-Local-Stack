import os
import pathlib
import subprocess
from app.core.config import settings

ROOT = pathlib.Path(settings.workspace_dir).resolve()


class AgentError(Exception):
    pass


def _safe(path: str) -> pathlib.Path:
    p = (ROOT / path).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise AgentError("Acesso fora do workspace bloqueado")
    return p


def list_dir(path: str = ".") -> list[str]:
    p = _safe(path)
    return sorted([x.name + ("/" if x.is_dir() else "") for x in p.iterdir()])


def read_file(path: str, max_bytes: int = 200_000) -> str:
    p = _safe(path)
    data = p.read_bytes()[:max_bytes]
    return data.decode("utf-8", errors="replace")


def write_file(path: str, content: str) -> str:
    if len(content.encode()) > settings.max_edit_bytes:
        raise AgentError("Arquivo excede limite de edição")
    p = _safe(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"WROTE {p}"


def apply_patch(path: str, old: str, new: str) -> str:
    txt = read_file(path, max_bytes=settings.max_edit_bytes)
    if old not in txt:
        raise AgentError("Trecho old não encontrado")
    return write_file(path, txt.replace(old, new, 1))


def run_cmd(cmd: str, timeout: int = 60) -> str:
    if not settings.allow_shell:
        raise AgentError("Shell desabilitado por política")
    forbidden = ["rm -rf /", "mkfs", "dd if=", ":(){", "shutdown", "reboot", "format"]
    if any(f in cmd for f in forbidden):
        raise AgentError("Comando bloqueado")
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return out[-20000:]


def lint_python(path: str) -> str:
    p = _safe(path)
    return run_cmd(f"python3 -m py_compile '{p}'")
