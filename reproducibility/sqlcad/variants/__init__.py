"""SQLCAD CAD variants used by the reproducibility package.

Each module implements one of the approaches from the notebooks and exposes:

- ``NAME``: the label used for the generated timings CSV.
- ``solve(con, dimensions)``: build a CAD for the ReLU instance with the given
  number of dimensions (inputs plus the output variable) and return ``"sat"``
  or ``"unsat"``.

``column_intermediate`` additionally exposes ``solve_constraints`` and
``generate_constraints_for_dimensions`` so it can be re-used for the dense
constraint experiments.
"""
