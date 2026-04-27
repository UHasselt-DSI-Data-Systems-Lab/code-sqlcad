import duckdb as db

DBNAME = "dbs/cad_basic.db"

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

    with open('queries/basic/recursive_template.sql') as file:
        query_template = file.read()

    fol_parts = [f"SELECT input_id FROM results WHERE description = 'u-{k}' AND result > 0"]
    for i in range(1, dimensions + 1):
        fol_parts.append(f"SELECT input_id FROM results WHERE description = 'x{i}-{k}' AND result < 0")

    fol_part = " INTERSECT ".join(fol_parts)

    return query_template.format(sat_input_ids=fol_part)


import util.perftest as perftest

def perftest_until_n(n: int, force=True, output_dir="timings"):
    with db.connect(DBNAME) as con:
        class BasicPerfTest(perftest.PerfTest):
            def name(self):
                return "basic_recursive"

            def setup_run(self, dimensions):
                # Note that we do `dimension - 1`, because our generator function is
                # named a bit unfortunate. `dimensions` are the number of arguments
                # to the function F we are testing, so including an output variable
                # we have an extra dimension.
                generate_scenario_with_dimensions(con, dimensions - 1)

            def run(self, dimensions):
                query = generate_query_with_dimensions(dimensions - 1)
                results = con.execute(query)

            def x_labels(self):
                return range(2, n+1)

        perftest.measure_performance(BasicPerfTest(), force=force, output_dir=output_dir)


# We see some very pessimistic scaling here. But, this approach is a first step.
# In later notebooks, we will explore some optimizations and things look better
# --- though we can't escape the exponential scaling.
