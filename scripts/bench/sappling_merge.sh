#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sappling-merge}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sappling.cli init . >/dev/null
cat <<'TXT' > file.txt
base
TXT

python3 -m sappling.cli add file.txt >/dev/null
python3 -m sappling.cli commit -m base >/dev/null

python3 -m sappling.cli branch feature >/dev/null
python3 -m sappling.cli checkout feature >/dev/null
cat <<'TXT' > file.txt
feature
TXT
python3 -m sappling.cli add file.txt >/dev/null
python3 -m sappling.cli commit -m feature >/dev/null

python3 -m sappling.cli checkout master >/dev/null
python3 -m sappling.cli merge feature >/dev/null
