#!/bin/bash
set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <project number: 1 or 2>"
    exit 1
fi

cd "$(dirname "$0")/.."

export PATH="$HOME/.cargo/bin:$PATH"

python3 src/run_pipeline.py "$1"
