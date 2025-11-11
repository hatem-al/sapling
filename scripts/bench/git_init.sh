#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/git-init}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

git init -q .
