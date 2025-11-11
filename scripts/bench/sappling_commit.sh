#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sappling-commit}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sappling.cli init . >/dev/null
cat <<'TXT' > file.txt
hello
TXT

python3 -m sappling.cli add file.txt >/dev/null
GIT_AUTHOR_NAME="Bench" GIT_AUTHOR_EMAIL="bench@example.com" \
GIT_COMMITTER_NAME="Bench" GIT_COMMITTER_EMAIL="bench@example.com" \
python3 -m sappling.cli commit -m "bench commit" >/dev/null
