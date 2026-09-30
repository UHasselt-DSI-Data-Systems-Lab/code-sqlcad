#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPRO_DIR = HERE.parent
sys.path.insert(0, str(REPRO_DIR))
sys.path.insert(0, str(HERE))

import duckdb as db  # noqa: E402

import experiments  # noqa: E402
import perf  # noqa: E402
from variants import (  # noqa: E402
    basic_nonrecursive,
    basic_recursive,
    column_based,
    column_intermediate,
)

OUTPUT_DIR = HERE / "timings"

DENSE_VARIANT = column_intermediate
DIMENSION_VARIANTS = [
    basic_recursive,
    basic_nonrecursive,
    column_based,
    column_intermediate,
]


def run_dense(con):
    for scenario, generate in experiments.DENSE_GENERATORS.items():
        perf.measure(
            scenario,
            lambda n, generate=generate: DENSE_VARIANT.solve_constraints(
                con, generate(n)
            ),
            output_dir=OUTPUT_DIR,
            sizes=experiments.sizes(scenario, DENSE_VARIANT.NAME),
            repetitions=experiments.REPETITIONS,
        )


def run_dimensions(con):
    for variant in DIMENSION_VARIANTS:
        perf.measure(
            variant.NAME,
            lambda k, variant=variant: variant.solve(con, k),
            output_dir=OUTPUT_DIR,
            sizes=experiments.sizes("dimensions", variant.NAME),
            repetitions=experiments.REPETITIONS,
        )


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

    with db.connect(":memory:") as con:
        if "dense" in groups:
            run_dense(con)
        if "dimensions" in groups:
            run_dimensions(con)


if __name__ == "__main__":
    main()
