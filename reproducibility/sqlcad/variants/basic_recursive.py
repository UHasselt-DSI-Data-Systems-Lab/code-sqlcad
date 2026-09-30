from pathlib import Path

NAME = "basic_recursive"

QUERIES_DIR = Path(__file__).resolve().parent.parent / "queries/basic"


def create_db_with_constraints(con, constraints):
    con.sql("DROP TABLE IF EXISTS LinearConstraint")
    con.sql("""
        CREATE TABLE LinearConstraint(
            id INTEGER PRIMARY KEY,
            description VARCHAR NOT NULL
        )
    """)

    con.sql("DROP TABLE IF EXISTS Coefficient")
    con.sql("""
        CREATE TABLE Coefficient(
            constraint_id VARCHAR NOT NULL, -- VARCHAR omdat we dingen zoals 1x2 willen doen
            dimension INTEGER NOT NULL,
            value DOUBLE NOT NULL,
            PRIMARY KEY (constraint_id, dimension)
        )
    """)


    for constraint_id, coeffs in enumerate(constraints):
        con.execute("""
            INSERT INTO LinearConstraint(id, description)
            VALUES ($id, $description)
        """, {'id': constraint_id, 'description': coeffs[0]})

        for dimension, coeff_value in enumerate(coeffs[1:]):
            con.execute("""
                INSERT INTO Coefficient(constraint_id, dimension, value)
                VALUES ($constraint_id, $dimension, $value)
            """, {'constraint_id': constraint_id, 'dimension': dimension, 'value': coeff_value})

def generate_scenario_with_dimensions(con, dimensions):
    """
    Generalizes the formula:

    ∃x1,...,xk . (F(x1, ..., xk)) > k ∧ (x1 < k) ∧ ... ∧ (xk < k)

    Where F() is the ReLU of the summation, and k = dimensions - 1 (because the
    result of F() is given a new variable and thus a new dimension).
    """
    k = dimensions
    summation = ["+".join([f"x{i}" for i in range(1, dimensions + 1)]), 0] + [1 for _ in range(1, dimensions + 1)]
    out = ["u"] + [0 for _ in range(0, dimensions + 1)] + [1]
    relu = ["+".join([f"x{i}" for i in range(1, dimensions + 1)]) + "-u"] + [0] + [1 for _ in range(0, dimensions)] + [-1]

    lt_constraints = [[f"u-{k}", -k] + [0 for _ in range(0, dimensions)] + [1]]
    for i in range(1, dimensions + 1):
        lt_constraints.append([f"x{i}-{k}", -k] + [0 for _ in range(0, i-1)] + [1])

    constraints = [
        summation,
        out,
        relu
    ] + lt_constraints

    create_db_with_constraints(con, constraints)

def generate_query_with_dimensions(dimensions):
    k = dimensions

    with open(QUERIES_DIR / 'recursive_template.sql') as file:
        query_template = file.read()

    fol_parts = [f"SELECT input_id FROM results WHERE description = 'u-{k}' AND result > 0"]
    for i in range(1, dimensions + 1):
        fol_parts.append(f"SELECT input_id FROM results WHERE description = 'x{i}-{k}' AND result < 0")

    fol_part = " INTERSECT ".join(fol_parts)

    return query_template.format(sat_input_ids=fol_part)


def solve(con, dimensions):
    """Decide the ReLU instance with ``dimensions`` inputs (see experiments.py)."""
    generate_scenario_with_dimensions(con, dimensions)
    query = generate_query_with_dimensions(dimensions)
    return "sat" if con.execute(query).fetchall() else "unsat"
