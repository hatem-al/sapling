#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=${1:-/tmp/sappling-demo}

echo "[sappling-demo] Preparing fresh workspace at $REPO_DIR"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

sappling init .

echo "hello world" > hello.txt
sappling add hello.txt
sappling commit -m "Initial commit"

sappling branch feature
sappling checkout feature

echo "print('hi sappling')" > app.py
sappling add app.py
sappling commit -m "Add app skeleton"

sappling checkout master

echo "hello master" >> hello.txt
sappling add hello.txt
sappling commit -m "Touch base branch"

sappling merge feature || true

sappling status
sappling log

printf '\n[sappling-demo] Loose objects in .git/objects:\n'
find .git/objects -type f | sort

printf '\n[sappling-demo] Dump commit object via cat-file:\n'
LATEST=$(sappling log | head -n1 | awk '{print $2}')
sappling cat-file "$LATEST"
