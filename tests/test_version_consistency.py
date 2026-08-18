"""Garante que todos os componentes usam a mesma versão definida em VERSION."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.version import ISABEL_VERSION  # noqa: E402


def test_version_file_matches_module():
    version_file = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version_file == ISABEL_VERSION, (
        f"VERSION file ({version_file}) != app.version.ISABEL_VERSION ({ISABEL_VERSION})"
    )


def test_agent_default_version():
    agent_src = (ROOT / "client" / "windows" / "agent.py").read_text(encoding="utf-8")
    match = re.search(r'os\.getenv\(\s*"ISABEL_VERSION"\s*,\s*"([^"]+)"\s*\)', agent_src)
    assert match, "Não encontrou os.getenv('ISABEL_VERSION', ...) no agent.py"
    agent_version = match.group(1)
    assert agent_version == ISABEL_VERSION, (
        f"agent.py default ({agent_version}) != ISABEL_VERSION ({ISABEL_VERSION})"
    )


def test_version_format():
    assert re.match(r"^\d+\.\d+\.\d+$", ISABEL_VERSION), (
        f"Versão deve ser semver (X.Y.Z), recebido: {ISABEL_VERSION}"
    )
