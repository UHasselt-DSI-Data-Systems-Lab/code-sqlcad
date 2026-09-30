#!/usr/bin/env python3

# TODO: add dimensions experiments plot + fix plots (e.g. no need for tick at 5,
# different symbols, fix titles, etc).

from pathlib import Path

import altair as alt
import pandas as pd

HERE = Path(__file__).resolve().parent

BASELINES = ["sqlcad", "qepcad", "z3"]

EXPERIMENTS = {
    "dense_constraints": {
        "title": "dense_constraints (always SAT)",
        "x": "Number of constraints",
    },
    "dense_constraints_mixed": {
        "title": "dense_constraints (mixed SAT/UNSAT)",
        "x": "Number of constraints",
    },
    "dimensions": {
        "title": "dimensions",
        "x": "Number of dimensions",
    },
}


def load(experiment):
    frames = []
    for baseline in BASELINES:
        path = HERE / baseline / "timings" / f"{experiment}.csv"
        if not path.exists():
            print(f"  missing {path}, skipping")
            continue

        frame = pd.read_csv(path)
        frame["baseline"] = baseline
        frames.append(frame)

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    return (
        combined.groupby(["baseline", "x"], as_index=False)["time"]
        .agg(mean="mean", min="min", max="max")
    )


def plot(experiment, spec):
    summary = load(experiment)
    if summary is None:
        print(f"No data for '{experiment}', skipping.\n")
        return

    x = alt.X("x:Q", title=spec["x"], axis=alt.Axis(format="d"))
    y = alt.Y("mean:Q", title="Time (s)")

    points = (
        alt.Chart(summary)
        .mark_point(size=70, filled=True)
        .encode(x=x, y=y, color=alt.Color("baseline:N", title="Baseline"))
    )
    lines = (
        alt.Chart(summary)
        .mark_line(strokeDash=[6, 2])
        .encode(x=x, y=y, color=alt.Color("baseline:N", title="Baseline"))
    )

    chart = (
        (points + lines)
        .properties(width=600, height=400, title=spec["title"])
        .configure_axis(grid=False)
        .configure_view(strokeOpacity=0)
    )

    path = HERE / f"{experiment}.png"
    chart.save(path, scale_factor=2)
    print(f"Wrote {path}")


def main():
    for experiment, spec in EXPERIMENTS.items():
        print(f"Plotting {experiment}...")
        plot(experiment, spec)


if __name__ == "__main__":
    main()
