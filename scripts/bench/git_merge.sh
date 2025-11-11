#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/git-merge}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

git init -q .
cat <<'TXT' > file.txt
base
TXT

git add file.txt
git commit -q -m base

git checkout -q -b feature
cat <<'TXT' > file.txt
feature
TXT

git commit -am feature

git checkout -q master
git merge -q feature
