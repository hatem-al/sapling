#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sappling-init}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sappling.cli init . >/dev/null
