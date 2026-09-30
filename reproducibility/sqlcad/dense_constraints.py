#!/usr/bin/env python3
"""SQLCAD timings for the dense_constraints experiment.

Re-uses the column-based-intermediate CAD implementation from
``perftest-docker/impl_column_dense.py``. Each scenario is a decision problem:
is there a point (x1, x2) satisfying all constraints? The CAD marks every cell
with a truth value, so the formula is satisfiable iff at least one cell is true.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "perftest-docker"))
sys.path.insert(0, str(REPO_ROOT / "reproducibility"))

import duckdb as db  # noqa: E402

import experiments  # noqa: E402
import impl_column_dense as dense  # noqa: E402
import perf  # noqa: E402

DB = "/tmp/sqlcad_dense_constraints.db"
OUTPUT_DIR = Path(__file__).with_name("timings")


def solve(con, constraints):
    dense.create_cad(con, constraints)
    satisfiable = con.execute(
        "SELECT EXISTS(SELECT 1 FROM Result WHERE truth_value)"
    ).fetchone()[0]
    return "sat" if satisfiable else "unsat"


def main():
    with db.connect(DB) as con:
        for name, generate in experiments.DENSE_SCENARIOS.items():
            perf.measure(
                name,
                lambda num_constraints, generate=generate: solve(
                    con, generate(num_constraints)
                ),
                output_dir=OUTPUT_DIR,
                sizes=experiments.DENSE_CONSTRAINTS_SIZES,
                repetitions=experiments.REPETITIONS,
            )


if __name__ == "__main__":
    main()
