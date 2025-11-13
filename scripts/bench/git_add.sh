#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/git-add}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

git init -q .
python3 - <<'PY'
from pathlib import Path
Path('file.txt').write_text('hello git\n')
PY

git add file.txt
