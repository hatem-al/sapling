#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/git-merge}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

git init -q .
git checkout -q -b master
python3 - <<'PY'
from pathlib import Path
Path('file.txt').write_text('base\n', encoding='utf-8')
PY

git add file.txt
git commit -q -m base

git checkout -q -b feature
python3 - <<'PY'
from pathlib import Path
Path('file.txt').write_text('feature\n', encoding='utf-8')
PY

git commit -am feature

git checkout -q master
git merge -q feature
