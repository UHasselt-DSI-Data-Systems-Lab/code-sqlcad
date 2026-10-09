#!/usr/bin/env python3
"""Run the QEPCAD baseline for all experiments."""

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPRO_DIR = HERE.parent
sys.path.insert(0, str(REPRO_DIR))

import experiments  # noqa: E402
import perf  # noqa: E402

OUTPUT_DIR = HERE / "timings"

# +N<numcells>: SACLIB's garbage-collected space. The default is too small for
# the signed instances and makes QEPCAD abort with "Too few cells reclaimed".
QEPCAD_MEMORY = 10_000_000
QEPCAD_TIMEOUT = 300


def is_timeout(result):
    """Treat a timeout as a limit: stop increasing the problem size."""
    return result == "timeout"


def format_sum(terms):
    """Render a signed sum the way QEPCAD's parser expects.

    ``terms`` is a list of ``(coefficient, variable_or_None)`` pairs. QEPCAD
    uses implicit multiplication (``2 x``), not ``*``.
    """
    rendered = []
    for coeff, var in terms:
        if coeff == 0:
            continue
        magnitude = abs(coeff)
        if var is None:
            body = str(magnitude)
        else:
            body = var if magnitude == 1 else f"{magnitude} {var}"
        if not rendered:
            rendered.append(("-" if coeff < 0 else "") + body)
        else:
            rendered.append((" - " if coeff < 0 else " + ") + body)
    return "".join(rendered) or "0"


def run_qepcad(script):
    """Run QEPCAD on a prepared input script, returning its stdout."""
    try:
        proc = subprocess.run(
            ["qepcad", "-noecho", f"+N{QEPCAD_MEMORY}"],
            input=script,
            capture_output=True,
            text=True,
            timeout=QEPCAD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return None
    return proc.stdout


def parse_result(stdout):
    marker = "An equivalent quantifier-free formula:"
    tail = stdout.split(marker, 1)[1] if marker in stdout else stdout
    for token in tail.replace("\n", " ").split():
        if token == "TRUE":
            return "sat"
        if token == "FALSE":
            return "unsat"
        if set(token) == {"="}:
            break
    return None


def qepcad_decision(script):
    stdout = run_qepcad(script)
    if stdout is None:
        return "timeout"
    result = parse_result(stdout)
    if result is None:
        print(stdout[-2000:], file=sys.stderr)
        raise RuntimeError("Could not parse QEPCAD output.")
    return result


def build_dense_input(constraints):
    clauses = []
    for _, a0, a1, a2 in constraints:
        expr = format_sum([(a0, None), (a1, "x"), (a2, "y")])
        clauses.append(f"[{expr} > 0]")
    conjunction = " /\\ ".join(clauses)
    formula = f"(E x)(E y)[{conjunction}]."
    return "\n".join(["[]", "(x,y)", "0", formula, "finish"]) + "\n"


def solve_dense(constraints):
    return qepcad_decision(build_dense_input(constraints))


def build_dimensions_input(dimensions):
    """Build the ReLU instance with ``dimensions`` inputs for QEPCAD."""
    k = dimensions
    xs = [f"x{i}" for i in range(1, k + 1)]
    summation = format_sum([(1, x) for x in xs])

    relu_low = f"[[{summation} < 0] /\\ [u = 0]]"
    relu_high = f"[[{summation} >= 0] /\\ [{summation} - u = 0]]"
    relu = f"[{relu_low} \\/ {relu_high}]"
    output = format_sum([(-k, None), (1, "u")])
    clauses = [relu, f"[{output} > 0]"]
    for x in xs:
        clauses.append(f"[{format_sum([(-k, None), (1, x)])} < 0]")

    formula = "".join(f"(E {x})" for x in xs + ["u"]) + "[" + " /\\ ".join(clauses) + "]."
    variables = "(" + ",".join(xs + ["u"]) + ")"
    return "\n".join(["[]", variables, "0", formula, "finish"]) + "\n"


def solve_dimensions(dimensions):
    return qepcad_decision(build_dimensions_input(dimensions))


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
                sizes=experiments.sizes(scenario, "qepcad"),
                repetitions=experiments.REPETITIONS,
                stop_on=is_timeout,
            )

    if "dimensions" in groups:
        perf.measure(
            "dimensions",
            solve_dimensions,
            output_dir=OUTPUT_DIR,
            sizes=experiments.sizes("dimensions", "qepcad"),
            repetitions=experiments.REPETITIONS,
            stop_on=is_timeout,
        )


if __name__ == "__main__":
    main()
