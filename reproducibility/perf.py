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

    if warmup:
        run(sizes[0])

    rows = []
    print(f"{name}:")
    print(f"{'x':>4} | {'mean (s)':>10} | {'min (s)':>10} | result")
    print("-" * 44)

    for x in sizes:
        times = []
        results = []
        for n in range(repetitions):
            start = time.perf_counter()
            result = run(x)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            results.append(result)
            rows.append({"N": n, "x": x, "time": elapsed, "result": result})

        print(f"{x:>4} | {statistics.mean(times):>10.4f} | {min(times):>10.4f} | {results[0]}")

    csv_path = output_dir / f"{name}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["N", "x", "time", "result"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {csv_path}\n")
    return rows
