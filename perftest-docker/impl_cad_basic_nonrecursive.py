import duckdb as db

DBNAME = "dbs/cad_basic_nonrecursive.db"


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
            constraint_id VARCHAR NOT NULL,
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


def generate_nonrecursive_query_with_dimensions(dimensions):
    k = dimensions
    max_dim = k + 1

    lines = []
    lines.append("WITH")

    lines.append(f"proj_dim_{max_dim} AS (")
    lines.append(f"    SELECT CAST(constraint_id AS VARCHAR) AS constraint_id, dimension, value FROM Coefficient")
    lines.append(f"),")

    for d in range(max_dim, 1, -1):
        prev = d - 1
        lines.append(f"dim_{d}_coeffs AS (")
        lines.append(f"    SELECT * FROM proj_dim_{d}")
        lines.append(f"    WHERE dimension = {d} AND value <> 0")
        lines.append(f"),")

        lines.append(f"dim_{d}_normalized AS (")
        lines.append(f"    SELECT")
        lines.append(f"        c.constraint_id,")
        lines.append(f"        c.dimension,")
        lines.append(f"        c.value / zc.value AS value")
        lines.append(f"    FROM proj_dim_{d} c")
        lines.append(f"    JOIN dim_{d}_coeffs zc ON c.constraint_id = zc.constraint_id")
        lines.append(f"        AND c.dimension < zc.dimension")
        lines.append(f"),")

        lines.append(f"dim_{d}_intersects AS (")
        lines.append(f"    SELECT")
        lines.append(f"        (nc1.constraint_id || 'x' || nc2.constraint_id) AS constraint_id,")
        lines.append(f"        nc1.dimension,")
        lines.append(f"        nc2.value - nc1.value AS value")
        lines.append(f"    FROM dim_{d}_normalized nc1")
        lines.append(f"    JOIN dim_{d}_normalized nc2")
        lines.append(f"        ON nc1.constraint_id <> nc2.constraint_id")
        lines.append(f"        AND nc1.constraint_id < nc2.constraint_id")
        lines.append(f"        AND nc1.dimension = nc2.dimension")
        lines.append(f"),")

        lines.append(f"proj_dim_{prev} AS (")
        lines.append(f"    SELECT * FROM proj_dim_{d}")
        lines.append(f"    WHERE constraint_id NOT IN (SELECT constraint_id FROM dim_{d}_coeffs)")
        lines.append(f"    UNION ALL")
        lines.append(f"    SELECT * FROM dim_{d}_intersects zc1")
        lines.append(f"    WHERE EXISTS (")
        lines.append(f"        SELECT 1 FROM dim_{d}_intersects zc2")
        lines.append(f"        WHERE zc1.constraint_id = zc2.constraint_id")
        lines.append(f"        AND zc2.dimension > 0")
        lines.append(f"        AND zc2.value <> 0")
        lines.append(f"    )")
        lines.append(f"),")

    proj_tables = " UNION ALL ".join(f"SELECT constraint_id, dimension, value FROM proj_dim_{d}" for d in range(1, max_dim + 1))
    lines.append(f"all_projections AS (")
    lines.append(f"    {proj_tables}")
    lines.append(f"),")

    lines.append(f"x_values AS (")
    lines.append(f"    SELECT DISTINCT -coeff0.value / coeff1.value AS x_value")
    lines.append(f"    FROM all_projections coeff0")
    lines.append(f"    JOIN all_projections coeff1")
    lines.append(f"        ON coeff0.constraint_id = coeff1.constraint_id")
    lines.append(f"        AND coeff0.dimension = 0")
    lines.append(f"        AND coeff1.dimension = 1")
    lines.append(f"        AND coeff1.value <> 0")
    lines.append(f"),")

    lines.append(f"x_intervals AS (")
    lines.append(f"    SELECT x_value AS interval_start, x_value AS interval_end")
    lines.append(f"    FROM x_values")
    lines.append(f"    UNION ALL")
    lines.append(f"    SELECT a.x_value AS interval_start, MIN(b.x_value) AS interval_end")
    lines.append(f"    FROM x_values a")
    lines.append(f"    JOIN x_values b ON b.x_value > a.x_value")
    lines.append(f"    GROUP BY a.x_value")
    lines.append(f"    UNION ALL")
    lines.append(f"    SELECT '-infinity'::DOUBLE, MIN(x_value) FROM x_values")
    lines.append(f"    UNION ALL")
    lines.append(f"    SELECT MAX(x_value), '+infinity'::DOUBLE FROM x_values")
    lines.append(f"),")

    lines.append(f"sample_points AS (")
    lines.append(f"    SELECT")
    lines.append(f"        CASE")
    lines.append(f"            WHEN ISINF(interval_start) THEN interval_end - 1.0")
    lines.append(f"            WHEN ISINF(interval_end) THEN interval_start + 1.0")
    lines.append(f"            ELSE (interval_start + interval_end) / 2.0")
    lines.append(f"        END AS sample_point")
    lines.append(f"    FROM x_intervals")
    lines.append(f"),")

    lines.append(f"sample_input_values AS (")
    lines.append(f"    SELECT ROW_NUMBER() OVER () AS input_id, 0 AS dimension, 1.0::DOUBLE AS value")
    lines.append(f"    FROM sample_points")
    lines.append(f"    UNION ALL")
    lines.append(f"    SELECT ROW_NUMBER() OVER () AS input_id, 1 AS dimension, sample_point AS value")
    lines.append(f"    FROM sample_points")
    lines.append(f"),")

    lines.append(f"lift_upto_dim_1 AS (")
    lines.append(f"    SELECT CAST(input_id AS VARCHAR) AS input_id, dimension, value")
    lines.append(f"    FROM sample_input_values")
    lines.append(f"),")

    for d in range(2, max_dim + 1):
        prev = d - 1
        dim_val = f"dim{d}_value"

        lines.append(f"dim_{d}_lift_normalized AS (")
        lines.append(f"    SELECT")
        lines.append(f"        c.constraint_id,")
        lines.append(f"        c.dimension,")
        lines.append(f"        c.value / -hd.value AS value")
        lines.append(f"    FROM proj_dim_{d} c")
        lines.append(f"    JOIN proj_dim_{d} hd")
        lines.append(f"        ON c.constraint_id = hd.constraint_id")
        lines.append(f"        AND hd.dimension = {d}")
        lines.append(f"        AND c.dimension < {d}")
        lines.append(f"        AND hd.value <> 0")
        lines.append(f"),")

        lines.append(f"dim_{d}_lift_eval AS (")
        lines.append(f"    SELECT")
        lines.append(f"        i.input_id,")
        lines.append(f"        SUM(i.value * xl.value) AS {dim_val}")
        lines.append(f"    FROM dim_{d}_lift_normalized xl")
        lines.append(f"    JOIN lift_upto_dim_{prev} i ON xl.dimension = i.dimension")
        lines.append(f"    GROUP BY i.input_id, xl.constraint_id")
        lines.append(f"),")

        lines.append(f"dim_{d}_inputs AS (")
        lines.append(f"    SELECT input_id, {dim_val}")
        lines.append(f"    FROM dim_{d}_lift_eval")
        lines.append(f"    GROUP BY input_id, {dim_val}")
        lines.append(f"),")

        lines.append(f"dim_{d}_intervals AS (")
        lines.append(f"    SELECT")
        lines.append(f"        input_id,")
        lines.append(f"        {dim_val} AS interval_start,")
        lines.append(f"        {dim_val} AS interval_end")
        lines.append(f"    FROM dim_{d}_inputs")
        lines.append(f"    UNION ALL")
        lines.append(f"    SELECT")
        lines.append(f"        a.input_id,")
        lines.append(f"        a.{dim_val} AS interval_start,")
        lines.append(f"        MIN(b.{dim_val}) AS interval_end")
        lines.append(f"    FROM dim_{d}_inputs a")
        lines.append(f"    JOIN dim_{d}_inputs b")
        lines.append(f"        ON a.input_id = b.input_id")
        lines.append(f"        AND b.{dim_val} > a.{dim_val}")
        lines.append(f"    GROUP BY a.input_id, a.{dim_val}")
        lines.append(f"    UNION ALL")
        lines.append(f"    SELECT input_id, '-infinity'::DOUBLE, MIN({dim_val})")
        lines.append(f"    FROM dim_{d}_inputs GROUP BY input_id")
        lines.append(f"    UNION ALL")
        lines.append(f"    SELECT input_id, MAX({dim_val}), '+infinity'::DOUBLE")
        lines.append(f"    FROM dim_{d}_inputs GROUP BY input_id")
        lines.append(f"),")

        lines.append(f"dim_{d}_sample_points AS (")
        lines.append(f"    SELECT")
        lines.append(f"        input_id,")
        lines.append(f"        ROW_NUMBER() OVER (PARTITION BY input_id ORDER BY interval_start) AS id,")
        lines.append(f"        CASE")
        lines.append(f"            WHEN ISINF(interval_start) THEN interval_end - 1.0")
        lines.append(f"            WHEN ISINF(interval_end) THEN interval_start + 1.0")
        lines.append(f"            ELSE (interval_start + interval_end) / 2.0")
        lines.append(f"        END AS value")
        lines.append(f"    FROM dim_{d}_intervals")
        lines.append(f"),")

        lines.append(f"lift_upto_dim_{d} AS (")
        lines.append(f"    SELECT")
        lines.append(f"        i.input_id || '_d{d}_' || sp.id AS input_id,")
        lines.append(f"        i.dimension,")
        lines.append(f"        i.value")
        lines.append(f"    FROM lift_upto_dim_{prev} i")
        lines.append(f"    JOIN dim_{d}_sample_points sp ON i.input_id = sp.input_id")
        lines.append(f"    UNION ALL")
        lines.append(f"    SELECT")
        lines.append(f"        input_id || '_d{d}_' || id AS input_id,")
        lines.append(f"        {d} AS dimension,")
        lines.append(f"        value")
        lines.append(f"    FROM dim_{d}_sample_points")
        lines.append(f"),")

    lines.append(f"all_cad_points AS (")
    lines.append(f"    SELECT * FROM lift_upto_dim_{max_dim}")
    lines.append(f"),")

    lines.append(f"results AS (")
    lines.append(f"    SELECT")
    lines.append(f"        c.constraint_id,")
    lines.append(f"        lc.description,")
    lines.append(f"        i.input_id,")
    lines.append(f"        SUM(i.value * c.value) AS result")
    lines.append(f"    FROM all_cad_points i")
    lines.append(f"    JOIN Coefficient c ON i.dimension = c.dimension")
    lines.append(f"    JOIN LinearConstraint lc ON c.constraint_id = lc.id")
    lines.append(f"    GROUP BY c.constraint_id, i.input_id, lc.description")
    lines.append(f"),")

    fol_parts = [f"SELECT input_id FROM results WHERE description = 'u-{k}' AND result > 0"]
    for i in range(1, k + 1):
        fol_parts.append(f"SELECT input_id FROM results WHERE description = 'x{i}-{k}' AND result < 0")
    fol_part = "\n    INTERSECT\n    ".join(fol_parts)

    lines.append(f"sat_input_ids AS (")
    lines.append(f"    {fol_part}")
    lines.append(f"),")

    lines.append(f"solutions AS (")
    lines.append(f"    SELECT * FROM all_cad_points")
    lines.append(f"    NATURAL JOIN sat_input_ids")
    lines.append(f"    WHERE dimension > 0")
    lines.append(f"    ORDER BY dimension")
    lines.append(f")")

    lines.append(f"SELECT * FROM solutions")
    lines.append(f"ORDER BY input_id, dimension")

    return "\n".join(lines)


import util.perftest as perftest


def perftest_until_n(n: int, force=True, output_dir="timings"):
    with db.connect(DBNAME) as con:
        class BasicNonRecursivePerfTest(perftest.PerfTest):
            def name(self):
                return "basic_nonrecursive"

            def setup_run(self, dimensions):
                generate_scenario_with_dimensions(con, dimensions - 1)

            def run(self, dimensions):
                query = generate_nonrecursive_query_with_dimensions(dimensions - 1)
                con.execute(query)

            def x_labels(self):
                return range(2, n + 1)

        perftest.measure_performance(BasicNonRecursivePerfTest(), force=force, output_dir=output_dir)
