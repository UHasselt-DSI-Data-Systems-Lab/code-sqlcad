#!/usr/bin/env python3
"""Run the Z3 baseline for all experiments."""

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPRO_DIR = HERE.parent
sys.path.insert(0, str(REPRO_DIR))

import z3  # noqa: E402

import experiments  # noqa: E402
import perf  # noqa: E402

OUTPUT_DIR = HERE / "timings"

def solve_dense(constraints):
    x, y = z3.Reals("x y")
    solver = z3.Solver()
    for _, a0, a1, a2 in constraints:
        solver.add(a0 + a1 * x + a2 * y > 0)

    return _check(solver)


def solve_dimensions(dimensions):
    xs = [z3.Real(f"x{i}") for i in range(1, dimensions + 1)]
    u = z3.Real("u")
    summation = z3.Sum(xs)

    solver = z3.Solver()
    solver.add(
        z3.Or(
            z3.And(summation < 0, u == 0),
            z3.And(summation >= 0, u == summation),
        )
    )
    solver.add(u > dimensions)
    for x in xs:
        solver.add(x < dimensions)

    return _check(solver)


def _check(solver):
    status = solver.check()
    if status == z3.sat:
        return "sat"
    if status == z3.unsat:
        return "unsat"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "groups",
        nargs="*",
        choices=["dense", "dimensions"],
        help="Experiment groups to run (default: all).",
    )
    args = parser.parse_args()
    groups = args.groups or ["dense", "dimensions"]

    if "dense" in groups:
        for scenario, generate in experiments.DENSE_GENERATORS.items():
            perf.measure(
                scenario,
                lambda n, generate=generate: solve_dense(generate(n)),
                output_dir=OUTPUT_DIR,
                sizes=experiments.sizes(scenario, "z3"),
                repetitions=experiments.REPETITIONS,
            )

    if "dimensions" in groups:
        perf.measure(
            "dimensions",
            solve_dimensions,
            output_dir=OUTPUT_DIR,
            sizes=experiments.sizes("dimensions", "z3"),
            repetitions=experiments.REPETITIONS,
        )


if __name__ == "__main__":
    main()
