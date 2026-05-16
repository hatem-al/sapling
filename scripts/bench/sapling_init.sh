#!/usr/bin/env bash
set -euo pipefail

TARGET=${1:-/tmp/bench/sapling-init}
rm -rf "$TARGET"
mkdir -p "$TARGET"
cd "$TARGET"

python3 -m sapling.cli init . >/dev/null
