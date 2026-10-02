#!/usr/bin/env python3

# TODO: check plot output compared to original (e.g. ticks, no log scale, etc)

from pathlib import Path

import altair as alt
import pandas as pd

HERE = Path(__file__).resolve().parent

EXPERIMENTS = {
    "dense_constraints": {
        "title": "dense_constraints (always SAT)",
        "x": "Number of constraints",
        "series": [
            ("sqlcad", "SQLCAD", "sqlcad/timings/dense_constraints.csv"),
            ("qepcad", "QEPCAD", "qepcad/timings/dense_constraints.csv"),
            ("z3", "Z3", "z3/timings/dense_constraints.csv"),
        ],
    },
    "dense_constraints_mixed": {
        "title": "dense_constraints (mixed SAT/UNSAT)",
        "x": "Number of constraints",
        "series": [
            ("sqlcad", "SQLCAD", "sqlcad/timings/dense_constraints_mixed.csv"),
            ("qepcad", "QEPCAD", "qepcad/timings/dense_constraints_mixed.csv"),
            ("z3", "Z3", "z3/timings/dense_constraints_mixed.csv"),
        ],
    },
    "dimensions": {
        "title": "CAD variant comparison",
        "x": "Number of dimensions",
        "series": [
            (
                "basic_recursive",
                "Row-based recursive",
                "sqlcad/timings/basic_recursive.csv",
            ),
            (
                "basic_nonrecursive",
                "Row-based non-recursive",
                "sqlcad/timings/basic_nonrecursive.csv",
            ),
            (
                "column_based",
                "Column-based recursive",
                "sqlcad/timings/column_based.csv",
            ),
            (
                "column_intermediate",
                "Column-based non-recursive",
                "sqlcad/timings/column_intermediate.csv",
            ),
            ("qepcad", "QEPCAD", "qepcad/timings/dimensions.csv"),
            ("z3", "Z3", "z3/timings/dimensions.csv"),
        ],
    },
}


def load(spec):
    frames = []
    for _, label, relative_path in spec["series"]:
        path = HERE / relative_path
        if not path.exists():
            print(f"  missing {path}, skipping")
            continue

        frame = pd.read_csv(path)
        frame["series"] = label
        frames.append(frame)

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    return (
        combined.groupby(["series", "x"], as_index=False)["time"]
        .agg(mean="mean", min="min", max="max")
    )


def plot(experiment, spec):
    summary = load(spec)
    if summary is None:
        print(f"No data for '{experiment}', skipping.\n")
        return

    x = alt.X(
        "x:Q",
        title=spec["x"],
        axis=alt.Axis(format="d"),
        scale=alt.Scale(zero=False),
    )
    y = alt.Y("mean:Q", title="Time (s)")
    domain = summary["series"].drop_duplicates().tolist()
    color = alt.Color(
        "series:N", title="Method", scale=alt.Scale(domain=domain)
    )
    shape = alt.Shape(
        "series:N", title="Method", scale=alt.Scale(domain=domain)
    )

    points = (
        alt.Chart(summary)
        .mark_point(size=70, filled=True)
        .encode(x=x, y=y, color=color, shape=shape)
    )
    lines = (
        alt.Chart(summary)
        .mark_line(strokeDash=[6, 2])
        .encode(x=x, y=y, color=color)
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
