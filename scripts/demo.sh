#!/usr/bin/env bash
set -euo pipefail

REPO_DIR=${1:-/tmp/sapling-demo}

# Helpers ---------------------------------------------------------------
PROMPT="\033[1;32m❯\033[0m "

cmd() {
    echo ""
    printf "${PROMPT}"
    # type out the command character by character
    local text="$1"
    for ((i=0; i<${#text}; i++)); do
        printf '%s' "${text:$i:1}"
        sleep 0.04
    done
    echo ""
    sleep 0.2
    eval "$1"
    sleep 0.6
}

banner() {
    echo ""
    printf "\033[1;34m# %s\033[0m\n" "$1"
    sleep 0.4
}

# Setup -----------------------------------------------------------------
rm -rf "$REPO_DIR"
mkdir -p "$REPO_DIR"
cd "$REPO_DIR"

# 1. Init ---------------------------------------------------------------
banner "Initialize a new repository"
cmd "sapling init ."

# 2. First commit -------------------------------------------------------
banner "Stage and commit a file"
cmd "echo 'hello world' > hello.txt"
cmd "sapling add hello.txt"
cmd "sapling commit -m 'Initial commit'"

# 3. Branch & second commit ---------------------------------------------
banner "Create a feature branch"
cmd "sapling branch feature"
cmd "sapling checkout feature"
cmd "echo 'print(\"hello\")' > app.py"
cmd "sapling add app.py"
cmd "sapling commit -m 'Add app skeleton'"

# 4. Merge --------------------------------------------------------------
banner "Merge back into master"
cmd "sapling checkout master"
cmd "sapling merge feature"

# 5. Log ----------------------------------------------------------------
banner "Inspect history"
cmd "sapling log"

# 6. Git compatibility --------------------------------------------------
banner "Objects are byte-for-byte Git-compatible"
LATEST=$(sapling log | awk 'NR==1{print $2}')
cmd "git cat-file -p $LATEST"
