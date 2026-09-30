#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

docker build -t sqlcad-qepcad-baseline "$HERE"

docker run --rm \
    -v "$ROOT:/work" \
    -w /work \
    sqlcad-qepcad-baseline \
    python3 qepcad/baseline/compare_dense.py "$@"
