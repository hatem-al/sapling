#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=${1:-/tmp/sapling-demo}

echo "[sapling-demo] Preparing fresh workspace at $REPO_DIR"
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

sapling init .

echo "hello world" > hello.txt
sapling add hello.txt
sapling commit -m "Initial commit"

sapling branch feature
sapling checkout feature

echo "print('hi sapling')" > app.py
sapling add app.py
sapling commit -m "Add app skeleton"

sapling checkout master

echo "hello master" >> hello.txt
sapling add hello.txt
sapling commit -m "Touch base branch"

sapling merge feature || true

sapling status
sapling log

printf '\n[sapling-demo] Loose objects in .git/objects:\n'
find .git/objects -type f | sort

printf '\n[sapling-demo] Dump commit object via cat-file:\n'
LATEST=$(sapling log | head -n1 | awk '{print $2}')
sapling cat-file "$LATEST"
