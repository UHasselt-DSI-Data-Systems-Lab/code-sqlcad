#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

docker build -t sqlcad-baseline-z3 "$HERE"

docker run --rm \
    -v "$ROOT:/work" \
    -w /work \
    sqlcad-baseline-z3 \
    python3 reproducibility/z3/dense_constraints.py "$@"
