import altair as alt
import pandas as pd

# Part 1: plot constraint scaling from column_based_dense_constraints.csv
# timings.

df = pd.read_csv("simlab-timings/column_based_dense_constraints.csv")

max_s = df['time'].max().item()

x_axis = alt.Axis(values=list(range(0, 151, 10)))

points = (
    alt.Chart(df)
    .mark_circle(size=60, color="steelblue")
    .encode(
        x=alt.X("x:Q", title="Number of constraints", axis=x_axis),
        y=alt.Y("mean(time):Q", title="Time (s)"),
    )
)

regression = (
    alt.Chart(df)
    .mark_line(color="steelblue", strokeWidth=1.5, strokeDash=[6, 2])
    .encode(x=alt.X("x:Q", axis=x_axis), y=alt.Y("time:Q"))
    .transform_regression("x", "time", method="exp")
)

chart = (
    (points + regression)
    .properties(width=600, height=400)
    .configure_axis(grid=False)
    .configure_view(strokeOpacity=0)
)

chart.save("column_based_dense_constraints.png", scale_factor=2)

# Part 2: plot timing comparison from different methods.

files = {
    "Row-based recursive": "simlab-timings/basic_recursive.csv",
    "Col-based non-recursive": "simlab-timings/column_based_intermediates.csv",
    "Col-based recursive": "simlab-timings/column_based.csv",
}

parts = []
for name, path in files.items():
    d = pd.read_csv(path)
    d["method"] = name
    d["x"] += 1
    parts.append(d)

df2 = pd.concat(parts, ignore_index=True)

points2 = (
    alt.Chart(df2)
    .mark_circle(size=60)
    .encode(
        x=alt.X(
            "x:Q",
            title="Number of dimensions",
            axis=alt.Axis(values=list(range(3, 11, 1)), format="d"),
            scale=alt.Scale(domain=(3,10))),
        y=alt.Y("mean(time):Q", title="Time (s)", axis=alt.Axis(values=list(range(0, 31, 5)))),
        color=alt.Color("method:N", title="Method"),
    )
)

regression2 = (
    alt.Chart(df2)
    .mark_line(strokeWidth=1.5, strokeDash=[6, 2])
    .encode(
        x=alt.X("x:Q"),
        y=alt.Y("time:Q"),
        color=alt.Color("method:N"),
    )
    .transform_regression("x", "time", method="exp", groupby=["method"])
)

chart2 = (
    (points2 + regression2)
    .properties(width=600, height=400)
    .configure_axis(grid=False)
    .configure_view(strokeOpacity=0)
    .configure_legend(orient="none", legendX=40, legendY=20)
)

chart2.save("method_comparison.png", scale_factor=2)
