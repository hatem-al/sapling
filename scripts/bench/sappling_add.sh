#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sappling-add}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sappling.cli init . >/dev/null
python3 - <<'PY'
from pathlib import Path
Path('file.txt').write_text('hello sappling\n')
PY

python3 -m sappling.cli add file.txt >/dev/null
