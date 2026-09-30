#!/usr/bin/env bash
set -euo pipefail
unset CDPATH

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

docker build -t sqlcad-baseline-qepcad "$HERE"

docker run --rm \
    -v "$ROOT:/work" \
    -w /work \
    sqlcad-baseline-qepcad \
    python3 reproducibility/qepcad/run.py "$@"
