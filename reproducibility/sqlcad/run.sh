#!/usr/bin/env bash
set -euo pipefail
unset CDPATH

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

docker build -t sqlcad-baseline-sqlcad "$HERE"

docker run --rm \
    -v "$ROOT:/work" \
    -w /work \
    sqlcad-baseline-sqlcad \
    python3 reproducibility/sqlcad/run.py "$@"
