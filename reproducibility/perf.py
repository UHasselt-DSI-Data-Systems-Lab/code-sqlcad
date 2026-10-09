"""
Minimal timing framework shared by all reproducibility baselines.
"""

import csv
import statistics
import sys
import time
from pathlib import Path


def measure(
    name,
    run,
    output_dir,
    sizes,
    repetitions,
    warmup=True,
    stop_on=None,
):
    """Time ``run`` over ``sizes`` and write the results to ``name.csv``.

    ``stop_on`` is an optional predicate on the result; the first result that
    satisfies it, as well as any exception raised by ``run``, is treated as a
    limit: no timing is recorded for it and no larger size is attempted.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{name}.csv"

    if warmup:
        try:
            run(sizes[0])
        except Exception as exc:
            print(f"{name}: warm-up at x={sizes[0]} failed: {exc!r}",
                  file=sys.stderr)

    fieldnames = ["N", "x", "time", "result"]
    rows = []
    print(f"{name}:")
    print(f"{'x':>4} | {'mean (s)':>10} | {'min (s)':>10} | result")
    print("-" * 44)

    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for x in sizes:
            times = []
            results = []
            hit_limit = False
            for n in range(repetitions):
                start = time.perf_counter()
                try:
                    result = run(x)
                except Exception as exc:
                    print(f"{name}: x={x} failed: {exc!r}", file=sys.stderr)
                    hit_limit = True
                    break
                elapsed = time.perf_counter() - start

                if stop_on is not None and stop_on(result):
                    print(f"{name}: x={x} hit limit ({result})",
                          file=sys.stderr)
                    hit_limit = True
                    break

                row = {"N": n, "x": x, "time": elapsed, "result": result}
                times.append(elapsed)
                results.append(result)
                rows.append(row)
                writer.writerow(row)

            handle.flush()
            if times:
                print(
                    f"{x:>4} | {statistics.mean(times):>10.4f} | "
                    f"{min(times):>10.4f} | {results[0]}"
                )
            else:
                print(f"{x:>4} | {'--':>10} | {'--':>10} | limit")

            if hit_limit:
                print(f"{name}: stopping before x>{x}\n")
                break

    print(f"\nWrote {csv_path}\n")
    return rows
