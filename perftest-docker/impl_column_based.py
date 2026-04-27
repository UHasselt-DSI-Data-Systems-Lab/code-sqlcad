import duckdb as db
import copy

DBNAME = "dbs/cad_columns.db"

def generate_db_for_dimensions(con, dimensions):
    create_table_sql = """
        CREATE TABLE LinearConstraint(
            id INTEGER PRIMARY KEY,
            description VARCHAR NOT NULL,
    """
    for i in range(0, dimensions + 2):
        create_table_sql += f"a{i} DOUBLE DEFAULT 0.0,"

    create_table_sql += ")"

    con.sql("DROP TABLE IF EXISTS LinearConstraint")
    con.sql(create_table_sql)

    constraints = []

    sum_all = ["+".join(f"x{i}" for i in range (1, dimensions+1))]
    sum_all += [0] + [1 for _ in range (0, dimensions)] + [0]
    constraints.append(sum_all)

    sum_all_minus_output = copy.copy(sum_all)
    sum_all_minus_output[0] += "-u"
    sum_all_minus_output[-1] = -1
    constraints.append(sum_all_minus_output)

    k = dimensions
    for i in range(1, dimensions + 1):
        constraint = [f"x{i}-{k}", -k]
        constraint += [0 for _ in range(1, i)]
        constraint += [1]
        constraint += [0 for _ in range(i, dimensions + 1)]
        constraints.append(constraint)

    output_constraint = [f"u-{k}", -k]
    output_constraint += [0 for i in range(0, dimensions)]
    output_constraint += [1]
    constraints.append(output_constraint)

    output = ["u"]
    output += [0 for _ in range(0, dimensions + 1)]
    output += [1]
    constraints.append(output)

    insert_query = """
        INSERT INTO LinearConstraint(id, description,
    """
    insert_query += ", ".join(f"a{i}" for i in range(0, dimensions + 2))
    insert_query += ") VALUES ("
    insert_query += ", ".join("?" for i in range(0, dimensions + 4))
    insert_query += ")"

    for id, constraint in enumerate(constraints, start=1):
        con.execute(insert_query, [id] + constraint)

def generate_query_for_dimensions(dimensions):
    with open('queries/column-based/template.sql') as file:
        template = file.read()

    all_coeff_columns = ", ".join(f"a{i}" for i in range(0, dimensions + 2))
    all_coeff_columns_prefixed = ", ".join(f"p.a{i}" for i in range(0, dimensions + 2))

    constraint_dimension_definition = "CASE\n"
    for i in range(1, dimensions + 2):
        k = dimensions + 2 - i
        constraint_dimension_definition += f"WHEN a{k} <> 0 THEN {k}\n"
    constraint_dimension_definition += "ELSE 0\n"
    constraint_dimension_definition += "END"

    intersect_norm_and_calc = ""
    for i in range(0, dimensions + 1):
        intersect_norm_and_calc += "CASE"

        for j in range(i, dimensions + 1):
            projdim = j + 1
            intersect_norm_and_calc += f"""
    WHEN a.dim_to_project = {projdim}
    THEN (a.a{i} / a.a{projdim}) - (b.a{i} / b.a{projdim})\n
"""
        intersect_norm_and_calc += "ELSE 0\n"
        intersect_norm_and_calc += f"END AS a{i},\n"

    intersect_norm_and_calc += f"0 AS a{dimensions + 1}"

    intersects_with_cd = "CASE\n"
    for i in range(1, dimensions+1):
        k = dimensions + 1 - i
        intersects_with_cd += f"  WHEN a{k} <> 0 THEN {k}\n"

    intersects_with_cd += "  ELSE 0\nEND"

    intersects_filter = " OR ".join(f"a{i} <> 0" for i in range(1, dimensions+2))

    default_vars = ",\n".join(f"0::DOUBLE AS x{i}" for i in range(2, dimensions+2))

    all_vars = ", ".join(f"x{i}" for i in range(1, dimensions+2))
    all_vars_prefixed = ", ".join(f"l.x{i}" for i in range(1, dimensions+2))
    all_vars_prefixed_a = ", ".join(f"a.x{i}" for i in range(1, dimensions+2))

    lift_calculate_variables = ""
    for i in range(2, dimensions + 2):
        lift_calculate_variables += "CASE\n"
        lift_calculate_variables += f"  WHEN d.dimension = {i}\n"

        ldim = i
        lift_calculate_variables += f"  THEN (p.a0  / - p.a{ldim})"
        for j in range(1, ldim):
            lift_calculate_variables += f" + (p.a{j} * l.x{j} / -p.a{ldim})"

        lift_calculate_variables += f"\n  ELSE l.x{i}\n"
        lift_calculate_variables += f"END AS x{i},\n"

    sample_points_calc = ""
    for i in range(2, dimensions + 2):
        sample_points_calc += "CASE\n"
        sample_points_calc += f"  WHEN a.dim_to_lift = {i}\n"
        sample_points_calc += f"  THEN (a.x{i} + MIN(b.x{i})) / 2\n"
        sample_points_calc += f"  ELSE a.x{i}\n"
        sample_points_calc += f"END AS x{i},\n"

    sample_points_join_1 = ""
    for i in range(2, dimensions + 2):
        sample_points_join_1 += f"AND IF(a.dim_to_lift > {i}, a.x{i} = b.x{i}, true)\n"

    sample_points_join_2 = "CASE\n"
    for i in range(2, dimensions + 2):
        sample_points_join_2 += f"  WHEN a.dim_to_lift = {i} THEN b.x{i} > a.x{i}\n"
    sample_points_join_2 += "END"

    lift_min_infinity_calc = ""
    for i in range(2, dimensions + 2):
        lift_min_infinity_calc += "CASE\n"
        lift_min_infinity_calc += f"  WHEN dim_to_lift = {i} THEN MIN(x{i}) - 1 ELSE x{i}\n"
        lift_min_infinity_calc += f"END AS x{i},\n"


    lift_plus_infinity_calc = ""
    for i in range(2, dimensions + 2):
        lift_plus_infinity_calc += "CASE\n"
        lift_plus_infinity_calc += f"  WHEN dim_to_lift = {i} THEN MAX(x{i}) + 1 ELSE x{i}\n"
        lift_plus_infinity_calc += f"END AS x{i},\n"

    sum_all_vars_times_all_coeffs = "a0"
    for i in range(1, dimensions + 2):
        sum_all_vars_times_all_coeffs += f" + a{i}*x{i}"

    select = f"SELECT {all_vars} FROM results"
    var_sum = "+".join(f"x{i}" for i in range(1, dimensions+1))
    compiled_formula = "(\n"
    # Definition of F
    compiled_formula += "  (\n"
    compiled_formula += f"    {select} WHERE description = '{var_sum}' AND result < 0\n"
    compiled_formula +=  "    INTERSECT\n"
    compiled_formula += f"    {select} WHERE description = 'u' AND result = 0\n"
    compiled_formula += "  )\n"
    compiled_formula += "  UNION\n"
    compiled_formula += "  (\n"
    compiled_formula += f"    {select} WHERE description = '{var_sum}' AND result >= 0\n"
    compiled_formula +=  "    INTERSECT\n"
    compiled_formula += f"    {select} WHERE description = '{var_sum}-u' AND result = 0\n"
    compiled_formula += "  )\n"
    compiled_formula += ")\n"
    compiled_formula += "INTERSECT\n"
    # Conditions on vars
    compiled_formula += f"{select} WHERE description = 'u-{dimensions}' AND result > 0\n"

    for i in range(1, dimensions+1):
        compiled_formula += "INTERSECT\n"
        compiled_formula += f"{select} WHERE description = 'x{i}-{dimensions}' AND result < 0\n"

    return template.format(
        max_dimension=dimensions+1,
        all_coeff_columns=all_coeff_columns,
        all_coeff_columns_prefixed=all_coeff_columns_prefixed,
        constraint_dimension_definition=constraint_dimension_definition,
        intersect_norm_and_calc=intersect_norm_and_calc,
        intersects_with_cd=intersects_with_cd,
        intersect_filter=intersects_filter,
        default_vars=default_vars,
        all_vars=all_vars,
        all_vars_prefixed=all_vars_prefixed,
        all_vars_prefixed_a=all_vars_prefixed_a,
        lift_calculate_variables=lift_calculate_variables,
        sample_points_calc=sample_points_calc,
        sample_points_join_1=sample_points_join_1,
        sample_points_join_2=sample_points_join_2,
        lift_min_infinity_calc=lift_min_infinity_calc,
        lift_plus_infinity_calc=lift_plus_infinity_calc,
        sum_all_vars_times_all_coeffs=sum_all_vars_times_all_coeffs,
        compiled_formula=compiled_formula
    )

import util.perftest as perftest


def perftest_until_n(n: int, force=True, output_dir="timings"):
    with db.connect(DBNAME) as con:
        class ColumnPerfTest(perftest.PerfTest):
            def name(self):
                return "column_based"

            def setup_run(self, dimensions):
                # See the note above.
                generate_db_for_dimensions(con, dimensions - 1)

            def run(self, dimensions):
                query = generate_query_for_dimensions(dimensions - 1)
                results = con.execute(query)

            def x_labels(self):
                return range(2, n+1)

        perftest.measure_performance(ColumnPerfTest(), force=force, output_dir=output_dir)
