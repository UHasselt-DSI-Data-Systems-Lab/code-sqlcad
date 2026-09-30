"""
Test setup for each experiment.
"""

import random

SEED = 123
REPETITIONS = 3

DENSE_CONSTRAINTS_DIMENSIONS = 3
DENSE_CONSTRAINTS_BOUND = 100


def dense_constraints(
    num_constraints,
    dimensions=DENSE_CONSTRAINTS_DIMENSIONS,
    seed=SEED,
):
    """Always-satisfiable random linear constraints.

    A fixed random witness point ``p`` is drawn first. Every constraint is then
    generated so that ``p`` satisfies it with a strictly positive margin, making
    the conjunction satisfiable by construction (which removes the "unsat means
    stop early" shortcut). The normals still point in every direction, so the
    resulting arrangement of constraints is generic.
    """
    rng = random.Random(seed)
    num_variables = dimensions - 1
    witness = [
        rng.randint(-DENSE_CONSTRAINTS_BOUND, DENSE_CONSTRAINTS_BOUND)
        for _ in range(num_variables)
    ]

    constraints = []
    for i in range(num_constraints):
        normal = [
            rng.randint(-DENSE_CONSTRAINTS_BOUND, DENSE_CONSTRAINTS_BOUND)
            for _ in range(num_variables)
        ]
        margin = rng.randint(1, DENSE_CONSTRAINTS_BOUND)
        constant = margin - sum(a * p for a, p in zip(normal, witness))
        constraints.append([f"constraint_{i}", constant] + normal)

    return constraints


def dense_constraints_mixed(
    num_constraints,
    dimensions=DENSE_CONSTRAINTS_DIMENSIONS,
    seed=SEED,
):
    """Random signed linear constraints, giving a mix of SAT and UNSAT instances."""
    rng = random.Random(seed)
    return [
        [f"constraint_{i}"]
        + [
            rng.randint(-DENSE_CONSTRAINTS_BOUND, DENSE_CONSTRAINTS_BOUND)
            for _ in range(dimensions)
        ]
        for i in range(num_constraints)
    ]


# Scenario name -> constraint generator, used by the dense runners.
DENSE_GENERATORS = {
    "dense_constraints": dense_constraints,
    "dense_constraints_mixed": dense_constraints_mixed,
}


# TODO: test bigger sets once everything is set up.
EXPERIMENTS = {
    "dense_constraints": {"sizes": [10, 20, 30, 40]},
    "dense_constraints_mixed": {"sizes": [10, 20, 30, 40]},
    "dimensions": {"sizes": [3, 4, 5]},
}

SIZE_OVERRIDES = {
    # Stop earlier for things that blow up faster.
    ("dimensions", "basic_recursive"): [3, 4],
    ("dimensions", "column_based"): [3, 4],
    # Example for the full-scale runs:
    # ("dense_constraints", "qepcad"): [10, 20, 30, 40, 50],
}


def sizes(scenario, variant):
    """Size list for ``scenario``, overridable per ``variant``."""
    return SIZE_OVERRIDES.get((scenario, variant), EXPERIMENTS[scenario]["sizes"])
