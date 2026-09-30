# Reproducibility

We compare our SQL-based approach to 2 baselines:

- QEPCAD: the standard CAD implementation (to compare against CAD)
- Z3: an SMT solver (to compare against industry solvers)

All experiments run on the same test data, generated in
[`experiments.py`](./experiments.py). Timing collection and CSV output are
shared in [`perf.py`](./perf.py). Each baseline lives in its own folder with a
Docker image and a `run.sh`.

Only the `dense_constraints` experiment is implemented for now, in two
scenarios: an always-satisfiable set (`dense_constraints`) and a mixed
SAT/UNSAT set (`dense_constraints_mixed`). Each `run.sh` writes its timings to
`<baseline>/timings/<scenario>.csv`.

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
