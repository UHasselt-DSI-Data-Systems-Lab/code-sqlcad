"""
Minimal timing framework shared by all reproducibility baselines.
"""

import csv
import statistics
import time
from pathlib import Path


def measure(name, run, output_dir, sizes, repetitions, warmup=True):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{name}.csv"

    if warmup:
        run(sizes[0])

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
            for n in range(repetitions):
                start = time.perf_counter()
                result = run(x)
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                results.append(result)
                row = {"N": n, "x": x, "time": elapsed, "result": result}
                rows.append(row)
                writer.writerow(row)

            handle.flush()
            print(
                f"{x:>4} | {statistics.mean(times):>10.4f} | "
                f"{min(times):>10.4f} | {results[0]}"
            )

    print(f"\nWrote {csv_path}\n")
    return rows
