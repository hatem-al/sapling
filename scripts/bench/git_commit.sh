#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/git-commit}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

git init -q .
cat <<'TXT' > file.txt
hello
TXT

git add file.txt
GIT_AUTHOR_NAME="Bench" GIT_AUTHOR_EMAIL="bench@example.com" \
GIT_COMMITTER_NAME="Bench" GIT_COMMITTER_EMAIL="bench@example.com" \
git commit -q -m "bench commit"
