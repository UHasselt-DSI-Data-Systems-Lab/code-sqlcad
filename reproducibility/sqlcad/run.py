#!/usr/bin/env python3

import argparse
import sys
import threading
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

SQLCAD_TIMEOUT = 300


class QueryTimeout(Exception):
    """Raised when a solve exceeds its wall-clock budget."""


def timed(con, solve):
    """Wrap ``solve`` so each call is cancelled after SQLCAD_TIMEOUT seconds."""
    def run(n):
        stop = threading.Event()

        def watch():
            if stop.wait(SQLCAD_TIMEOUT):
                return
            while not stop.is_set():
                con.interrupt()
                stop.wait(0.5)

        watcher = threading.Thread(target=watch, daemon=True)
        watcher.start()
        try:
            return solve(n)
        except db.InterruptException as exc:
            raise QueryTimeout(
                f"solve exceeded {SQLCAD_TIMEOUT}s and was interrupted"
            ) from exc
        finally:
            stop.set()

    return run


def run_dense(con):
    for scenario, generate in experiments.DENSE_GENERATORS.items():
        def solve(n, generate=generate):
            return DENSE_VARIANT.solve_constraints(con, generate(n))

        perf.measure(
            scenario,
            timed(con, solve),
            output_dir=OUTPUT_DIR,
            sizes=experiments.sizes(scenario, DENSE_VARIANT.NAME),
            repetitions=experiments.REPETITIONS,
        )


def run_dimensions(con):
    for variant in DIMENSION_VARIANTS:
        def solve(k, variant=variant):
            return variant.solve(con, k)

        perf.measure(
            variant.NAME,
            timed(con, solve),
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
