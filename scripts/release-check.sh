#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
VERSION=$(cat VERSION | tr -d '[:space:]')
echo "VERSION = $VERSION"
FAIL=0
grep -q "ISABEL_VERSION = \"$VERSION\"" server/app/version.py || FAIL=1
grep -q "\"$VERSION\"" client/windows/agent.py || FAIL=1
python -m compileall -q server/app client/windows/agent.py || FAIL=1
if [ $FAIL -eq 0 ]; then
  echo "OK. git tag v$VERSION && git push origin v$VERSION"
else
  echo "Corriga erros antes da tag"
  exit 1
fi
