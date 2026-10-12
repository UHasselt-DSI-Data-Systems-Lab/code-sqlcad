# Reproducibility

We compare our SQL-based CAD approach to 2 baselines:

- QEPCAD: the standard CAD implementation (to compare against CAD)
- Z3: an SMT solver (to compare against industry solvers)

The SQLCAD code itself is also compared across the variants developed in the
notebooks:

- Row-based recursive
- Row-based non-recursive
- Column-based recursive
- Column-based non-recursive

## Usage

From the repository root:

```sh
reproducibility/sqlcad/run.sh
reproducibility/qepcad/run.sh
reproducibility/z3/run.sh
```

Requires Docker to be installed.

## Plotting

[`plot_timings.py`](./plot_timings.py) plots the graphs shown in the paper.
Usage (requires uv installed, run from repo root):

```sh
uv run python reproducibility/plot_timings.py
```
