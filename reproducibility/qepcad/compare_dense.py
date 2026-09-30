#!/usr/bin/env python3
import argparse
import random
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "perftest-docker"))

import duckdb as db  # noqa: E402
import impl_column_dense as dense  # noqa: E402


def generate_constraints(num_constraints, dimensions=3, signed=False, seed=123):
    rng = random.Random(seed)
    low = -100 if signed else 0
    return [
        [f"constraint_{i}"] + [rng.randint(low, 100) for _ in range(dimensions)]
        for i in range(num_constraints)
    ]


def run_sqlcad(con, constraints):
    start = time.perf_counter()
    dense.create_cad(con, constraints)
    satisfiable = con.execute(
        "SELECT EXISTS(SELECT 1 FROM Result WHERE truth_value)"
    ).fetchone()[0]
    return time.perf_counter() - start, bool(satisfiable)


def format_sum(terms):
    """Render a signed sum the way QEPCAD's parser expects."""
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


def constraint_to_qepcad(row):
    a0, a1, a2 = row[1], row[2], row[3]
    expr = format_sum([(a0, None), (a1, "x"), (a2, "y")])
    return f"[{expr} > 0]"


def build_qepcad_input(constraints):
    conjunction = " /\\ ".join(constraint_to_qepcad(row) for row in constraints)
    formula = f"(E x)(E y)[{conjunction}]."
    return "\n".join(["[]", "(x,y)", "0", formula, "finish"]) + "\n"


def parse_qepcad_result(stdout):
    marker = "An equivalent quantifier-free formula:"
    tail = stdout.split(marker, 1)[1] if marker in stdout else stdout
    for token in tail.replace("\n", " ").split():
        if token in ("TRUE", "FALSE"):
            return token == "TRUE"
        if set(token) == {"="}:
            break
    return None


def run_qepcad(constraints, binary="qepcad", memcells=8_000_000, timeout=600):
    script = build_qepcad_input(constraints)
    start = time.perf_counter()
    proc = subprocess.run(
        [binary, "-noecho", f"+N{memcells}"],
        input=script,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    return elapsed, parse_qepcad_result(proc.stdout), proc


def fmt(values):
    return f"{statistics.mean(values):.3f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[5, 10, 20, 30])
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--dimensions", type=int, default=3,
                        help="Number of coefficients per constraint (repo default 3).")
    parser.add_argument("--signed", action="store_true",
                        help="Allow negative coefficients to get SAT/UNSAT mixes.")
    parser.add_argument("--qepcad", default="qepcad")
    parser.add_argument("--qepcad-memcells", type=int, default=8_000_000,
                        help="Value for QEPCAD's +N (garbage-collected space).")
    parser.add_argument("--db", default="/tmp/sqlcad_compare.db")
    parser.add_argument("--csv", default=str(Path(__file__).with_name("results.csv")))
    args = parser.parse_args()

    print(f"QEPCAD: {args.qepcad}")
    print(f"Sizes: {args.sizes}  reps={args.reps}  signed={args.signed}")
    print()

    header = f"{'N':>4} | {'sqlcad mean':>11} | {'qepcad mean':>11} | {'speedup':>8} | {'agree':>5} | result"
    print(header)
    print("-" * len(header))

    rows = []
    with db.connect(args.db) as con:
        for n in args.sizes:
            constraints = generate_constraints(
                n, dimensions=args.dimensions, signed=args.signed
            )
            print(f"  running N={n} ...", flush=True)

            sql_times, sql_sats = [], []
            for _ in range(args.reps):
                t, sat = run_sqlcad(con, constraints)
                sql_times.append(t)
                sql_sats.append(sat)

            qe_times, qe_sats = [], []
            for _ in range(args.reps):
                t, sat, proc = run_qepcad(
                    constraints, binary=args.qepcad, memcells=args.qepcad_memcells
                )
                if sat is None:
                    print(proc.stdout[-2000:])
                    raise SystemExit("Could not parse QEPCAD output.")
                qe_times.append(t)
                qe_sats.append(sat)

            sql_sat = sql_sats[0]
            qe_sat = qe_sats[0]
            agree = all(s == sql_sat for s in sql_sats) and all(
                s == qe_sat for s in qe_sats
            ) and sql_sat == qe_sat
            speedup = statistics.mean(sql_times) / statistics.mean(qe_times)

            print(
                f"{n:>4} | {fmt(sql_times):>11} | {fmt(qe_times):>11} | "
                f"{speedup:>7.1f}x | {str(agree):>5} | "
                f"sqlcad={'SAT' if sql_sat else 'UNSAT'}, "
                f"qepcad={'SAT' if qe_sat else 'UNSAT'}"
            )

            rows.append(
                {
                    "n": n,
                    "sqlcad_mean": statistics.mean(sql_times),
                    "sqlcad_min": min(sql_times),
                    "qepcad_mean": statistics.mean(qe_times),
                    "qepcad_min": min(qe_times),
                    "speedup": speedup,
                    "agree": agree,
                    "sqlcad_sat": sql_sat,
                    "qepcad_sat": qe_sat,
                }
            )

    import csv

    with open(args.csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {args.csv}")
    if not all(row["agree"] for row in rows):
        raise SystemExit("Result mismatch between SQLCAD and QEPCAD!")


if __name__ == "__main__":
    main()
