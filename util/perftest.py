import os
import pandas as pd
import itertools
import time
import matplotlib.pyplot as plt


class PerfTest:
    def setup_all(self):
        pass

    def setup_run(self, x):
        pass

    def run(self, x):
        pass

    def x_labels(self):
        return []

    def name(self):
        return self.__class__.__name__


def _all_rows_present(df, N, x_labels):
    ns = range(0, N)
    all_combinations = list(itertools.product(x_labels, ns))
    all_combinations_df = pd.DataFrame(all_combinations, columns=["x", "N"])
    missing_combinations = all_combinations_df.merge(
        df, on=["x", "N"], how="left", indicator=True
    ).query('_merge == "left_only"')

    return missing_combinations.empty


def measure_performance(test, N=5, force=False):
    name = test.name()
    csv_name = f"timings/{name}.csv"

    if force and os.path.exists(csv_name):
        os.remove(csv_name)

    if os.path.exists(csv_name):
        df = pd.read_csv(csv_name)
    else:
        df = pd.DataFrame(
            {
                "N": pd.Series(dtype="int"),
                "x": pd.Series(dtype="int"),
                "time": pd.Series(dtype="float"),
            }
        )

    x_labels = test.x_labels()
    if _all_rows_present(df, N, x_labels):
        return df.groupby("x", as_index=False)["time"].mean()

    test.setup_all()

    for x in x_labels:
        # We only save all iterations in one go, so if one x is present, all xs
        # are present and we can skip.
        if (df["x"] == x).any():
            continue

        print(f"Starting iterations for x={x}", end="")

        new_rows = []
        for n in range(0, N):
            test.setup_run(x)
            start = time.perf_counter()
            test.run(x)
            stop = time.perf_counter()
            new_rows.append({"N": n, "x": x, "time": stop - start})
            print(".", end="")

        print("")

        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        df.to_csv(csv_name, index=False)

    return df.groupby("x", as_index=False)["time"].mean()


def plot_df(df, x_label):
    plt.plot(df['x'], df['time'], marker='o')

    for i, (x, y) in enumerate(zip(df['x'], df['time'])):
        plt.text(x, y, f'{y:.2f}', ha='center')

    plt.xlabel(x_label)
    plt.ylabel('Time (s)')
    plt.show()


def plot_dfs(dfs, x_label):
    for i, (df, df_label, marker) in enumerate(dfs):
        plt.plot(df['x'], df['time'], label=df_label, marker=marker)

        for i, (x, y) in enumerate(zip(df['x'], df['time'])):
            plt.text(x, y, f'{y:.2f}', ha='center')

    plt.xlabel(x_label)
    plt.ylabel('Time (s)')
    plt.legend()
    plt.show()
