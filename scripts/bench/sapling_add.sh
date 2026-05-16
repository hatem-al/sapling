#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sapling-add}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sapling.cli init . >/dev/null
python3 - <<'PY'
from pathlib import Path
Path('file.txt').write_text('hello sapling\n')
PY

python3 -m sapling.cli add file.txt >/dev/null
