#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "reproducibility"))

import experiments  # noqa: E402
import perf  # noqa: E402

# +N<numcells>: SACLIB's garbage-collected space. The default is too small for
# the signed instances and makes QEPCAD abort with "Too few cells reclaimed".
QEPCAD_MEMORY = 10_000_000

OUTPUT_DIR = Path(__file__).with_name("timings")


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


def build_input(constraints):
    clauses = []
    for _, a0, a1, a2 in constraints:
        expr = format_sum([(a0, None), (a1, "x"), (a2, "y")])
        clauses.append(f"[{expr} > 0]")
    conjunction = " /\\ ".join(clauses)
    formula = f"(E x)(E y)[{conjunction}]."
    return "\n".join(["[]", "(x,y)", "0", formula, "finish"]) + "\n"


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


def solve(constraints):
    script = build_input(constraints)
    proc = subprocess.run(
        ["qepcad", "-noecho", f"+N{QEPCAD_MEMORY}"],
        input=script,
        capture_output=True,
        text=True,
        timeout=600,
    )
    result = parse_result(proc.stdout)
    if result is None:
        print(proc.stdout[-2000:])
        raise RuntimeError("Could not parse QEPCAD output.")
    return result


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
