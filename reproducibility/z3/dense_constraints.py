#!/usr/bin/env python3

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "reproducibility"))

import z3  # noqa: E402

import experiments  # noqa: E402
import perf  # noqa: E402

OUTPUT_DIR = Path(__file__).with_name("timings")


def solve(constraints):
    x, y = z3.Reals("x y")
    solver = z3.Solver()
    for _, a0, a1, a2 in constraints:
        solver.add(a0 + a1 * x + a2 * y > 0)

    status = solver.check()
    if status == z3.sat:
        return "sat"
    if status == z3.unsat:
        return "unsat"
    return "unknown"


def main():
    for name, generate in experiments.DENSE_SCENARIOS.items():
        perf.measure(
            name,
            lambda num_constraints, generate=generate: solve(
                generate(num_constraints)
            ),
            output_dir=OUTPUT_DIR,
            sizes=experiments.DENSE_CONSTRAINTS_SIZES,
            repetitions=experiments.REPETITIONS,
        )


if __name__ == "__main__":
    main()
