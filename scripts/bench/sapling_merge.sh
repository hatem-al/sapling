#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sapling-merge}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sapling.cli init . >/dev/null
cat <<'TXT' > file.txt
base
TXT

python3 -m sapling.cli add file.txt >/dev/null
python3 -m sapling.cli commit -m base >/dev/null

python3 -m sapling.cli branch feature >/dev/null
python3 -m sapling.cli checkout feature >/dev/null
cat <<'TXT' > file.txt
feature
TXT
python3 -m sapling.cli add file.txt >/dev/null
python3 -m sapling.cli commit -m feature >/dev/null

python3 -m sapling.cli checkout master >/dev/null
python3 -m sapling.cli merge feature >/dev/null
